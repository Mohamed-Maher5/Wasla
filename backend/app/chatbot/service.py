import os
import time
from typing import List
 
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import select
from groq import Groq
 
# .env is also loaded here independently so os.getenv can reach it
load_dotenv(".env.groq")
 
from app.auth.models import User
from .models import KnowledgeDocument, DocumentChunk, ChatLog
from .embeddings import extract_text, chunk_text, embed_chunks, embed_query
from .schemas import SourceSnippet
 
# GROQ_API_KEY must be set in .env.groq
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
CHAT_MODEL = "llama-3.3-70b-versatile"
TOP_K = 5
 
 
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
    doc = KnowledgeDocument(
        department_id=department_id,
        filename=filename,
        uploaded_by=uploaded_by,
        status="uploaded"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
 
    try:
        # 2) Extract text
        raw_text = extract_text(file_bytes, filename)
 
        # 3) Split into chunks
        pieces = chunk_text(raw_text)
        if not pieces:
            doc.status = "failed"
            db.commit()
            return doc
 
        # 4) Embeddings in one batch
        vectors = embed_chunks(pieces)
 
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
 
    except Exception:
        doc.status = "failed"
        db.commit()
        raise  # let the router decide what error code to return
 
    return doc
 
 
# ---------------------------------------------------------------------------
# Agent question (day 3)
# ---------------------------------------------------------------------------
 
def ask_question(db: Session, question: str, user: User) -> dict:
    start = time.time()
 
    # 1) Embed the question
    query_vector = embed_query(question)
 
    # 2) Fetch the top K chunks — only from the user's own department.
    #    This is the most important security line in the whole file —
    #    without this filter, anyone could see another department's
    #    documents.
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.department_id == user.department_id)
        .order_by(DocumentChunk.embedding_vector.cosine_distance(query_vector))
        .limit(TOP_K)
    )
    top_chunks: List[DocumentChunk] = db.execute(stmt).scalars().all()
 
    if not top_chunks:
        answer = "Sorry, I couldn't find enough information in your department's knowledge base to answer that."
        sources = []
    else:
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
        department_id=user.department_id,
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
    answer that cites its source — exactly as required by use case 2.
    """
    context_blocks = "\n\n".join(
        f"[Source {i+1} - {c.document.filename}]\n{c.chunk_text}"
        for i, c in enumerate(chunks)
    )
 
    system_prompt = (
        "You are an internal assistant answering contact center agents in Arabic only. "
        "Answer only from the information provided below. If the information isn't "
        "there, say so explicitly. Keep the answer concise and cite its source "
        "(source number) at the end."
    )
 
    user_prompt = f"Available information:\n{context_blocks}\n\nQuestion: {question}"
 
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content
 
 
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
 