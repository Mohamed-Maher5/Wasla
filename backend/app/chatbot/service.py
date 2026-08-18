import re
import time
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy import select
from groq import Groq

from app.auth.models import User
from app.shared.config import settings
from .models import KnowledgeDocument, DocumentChunk, ChatLog
from .embeddings import extract_text, chunk_text, embed_chunks, embed_query
from .schemas import SourceSnippet

client = None
CHAT_MODEL = "qwen/qwen3.6-27b"
TOP_K = 5


def _get_groq_client():
    global client
    if client is None:
        if not settings.groq_llm_api_key:
            raise RuntimeError("GROQ_LLM_API_KEY is not set")
        client = Groq(api_key=settings.groq_llm_api_key)
    return client


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> and similar reasoning wrappers from LLM output."""
    return re.sub(r"<think>[\s\S]*?</think>", "", text).strip()


# ---------------------------------------------------------------------------
# Document upload (days 1 + 2 combined — upload runs the full pipeline)
# ---------------------------------------------------------------------------

def upload_document(
    db: Session,
    file_bytes: bytes,
    filename: str,
    department_id: int,
    uploaded_by: int
) -> KnowledgeDocument:

    # 1) Record the document first so it has an id even if something fails later
    print(f"[chatbot] Creating KnowledgeDocument row for '{filename}' in dept {department_id}")
    doc = KnowledgeDocument(
        department_id=department_id,
        filename=filename,
        uploaded_by=uploaded_by,
        status="uploaded"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    print(f"[chatbot] KnowledgeDocument created with id={doc.id}, status='uploaded'")

    try:
        # 2) Extract text
        print(f"[chatbot] Extracting text from '{filename}' ({len(file_bytes)} bytes)")
        raw_text = extract_text(file_bytes, filename)
        print(f"[chatbot] Extracted {len(raw_text)} chars of text")

        # 3) Split into chunks
        pieces = chunk_text(raw_text)
        print(f"[chatbot] Split into {len(pieces)} chunks")
        if not pieces:
            doc.status = "failed"
            db.commit()
            print(f"[chatbot] No chunks produced — marking as failed")
            return doc

        # 4) Embeddings in one batch
        print(f"[chatbot] Calling HF API to embed {len(pieces)} chunks...")
        vectors = embed_chunks(pieces)
        print(f"[chatbot] Received {len(vectors)} embedding vectors")

        # 5) Store each chunk with its vector
        for idx, (piece, vector) in enumerate(zip(pieces, vectors)):
            chunk = DocumentChunk(
                document_id=doc.id,
                department_id=department_id,
                chunk_text=piece,
                chunk_index=idx,
                embedding_vector=vector
            )
            db.add(chunk)

        doc.status = "embedded"
        db.commit()
        print(f"[chatbot] All {len(pieces)} chunks committed — document fully embedded")

    except Exception as exc:
        doc.status = "failed"
        db.commit()
        print(f"[chatbot] FAILED at stage: {type(exc).__name__}: {exc}")
        raise  # let the router decide what error code to return

    return doc


# ---------------------------------------------------------------------------
# Agent question (day 3)
# ---------------------------------------------------------------------------

def ask_question(db: Session, question: str, user: User, department_id: int) -> dict:
    start = time.time()

    # 1) Embed the question
    query_vector = embed_query(question)

    # 2) Fetch the top K chunks — DEPARTMENT ISOLATION: do not remove.
    #    The department_id is always resolved server-side by the router:
    #    - superadmin: from the explicit request param (validated to exist)
    #    - admin/agent: from the user's own JWT-derived department_id.
    #    Never trust a client-sent value directly — the router enforces this.
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.department_id == department_id)
        .order_by(DocumentChunk.embedding_vector.cosine_distance(query_vector))
        .limit(TOP_K)
    )

    top_chunks: List[DocumentChunk] = db.execute(stmt).scalars().all()

    answer = _generate_answer(question, top_chunks)
    sources = [
        SourceSnippet(
            chunk_id=c.id,
            document_id=c.document_id,
            filename=c.document.filename,
            snippet=c.chunk_text[:200]
        )
        for c in top_chunks
    ]

    latency_ms = int((time.time() - start) * 1000)

    # 3) Audit log — record every question and answer
    log = ChatLog(
        user_id=user.id,
        department_id=department_id,
        question=question,
        answer=answer,
        source_chunk_ids=",".join(str(c.id) for c in top_chunks),
        latency_ms=latency_ms
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "answer": answer,
        "sources": sources,
        "latency_ms": latency_ms,
        "log_id": log.id
    }


def _generate_answer(question: str, chunks: List[DocumentChunk]) -> str:
    """
    Builds context from the chunks and asks the LLM for a concise Arabic
    answer. Handles greetings/small talk naturally and refuses only when
    a knowledge-base question has no matching content.
    """
    if chunks:
        context_blocks = "\n\n".join(
            f"[Source {i+1} - {c.document.filename}]\n{c.chunk_text}"
            for i, c in enumerate(chunks)
        )
        user_prompt = (
            f"Available information:\n{context_blocks}\n\n"
            f"Question: {question}"
        )
    else:
        user_prompt = f"Question: {question}"

    system_prompt = (
        "You are an Arabic-speaking support assistant. Rules:\n"
        "- Answer ONLY in Arabic. Never use English.\n"
        "- For greetings (like \"ازيك\", \"مرحبا\", \"السلام عليكم\"), small talk, "
        "or general questions unrelated to the uploaded documents — respond "
        "naturally and briefly like a helpful assistant. Do NOT refuse these.\n"
        "- For questions answered using the provided documents: keep the answer "
        "concise and cite the source document name at the end like (المصدر: اسم_الملف).\n"
        "- For knowledge-base questions where the provided documents do NOT "
        "contain the answer: say explicitly that this information is not "
        "available in the uploaded documents.\n"
        "- Never fabricate information. Only use what is in the documents for "
        "knowledge-base questions."
    )

    response = _get_groq_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return _strip_thinking(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Feedback (thumbs up/down) — mentioned in use case 2 as a feedback loop
# ---------------------------------------------------------------------------

def submit_feedback(db: Session, log_id: int, feedback: str) -> None:
    if feedback not in ("up", "down"):
        raise ValueError("feedback must be 'up' or 'down'")

    log = db.get(ChatLog, log_id)
    if not log:
        raise ValueError("log_id not found")

    log.feedback = feedback
    db.commit()
