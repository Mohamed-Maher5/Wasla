import hashlib
import os
import re
import time
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from groq import Groq

from app.auth.models import User
from app.shared.config import settings
from .models import KnowledgeDocument, DocumentChunk, ChatLog, Conversation
from .embeddings import extract_pages, chunk_pages, embed_chunks, embed_query
from .schemas import SourceSnippet, ChatHistoryTurn

client = None
CHAT_MODEL = "qwen/qwen3.6-27b"
TOP_K = 8

# cosine_distance ranges 0 (identical) .. 2 (opposite). Anything above this
# is treated as "not actually relevant" so the model doesn't get handed
# unrelated chunks and cite them as if they were the source of a made-up
# answer. Raised from 0.8 → 1.1: 0.8 was cutting off chunks that WERE
# relevant just because the question was phrased differently from the
# document text (e.g. "الحالة 2" vs. "حالة الاستخدام"), causing real
# answers to be wrongly refused. Tune again if noise creeps back in.
MAX_RELEVANT_DISTANCE = 1.1

# How many prior turns of the current conversation to replay to the LLM so
# it has context (e.g. "and what about him?" referring to the previous
# question). Capped to control token cost/latency.
MAX_HISTORY_TURNS = 8


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

def _compute_content_hash(pages: List[tuple]) -> str:
    """
    Hashes the normalized extracted text (not the raw file bytes), so two
    files that were saved differently (different PDF metadata, whitespace,
    etc.) but contain the same actual content are still recognized as
    duplicates.
    """
    normalized = "\n".join(text.strip() for _, text in pages if text and text.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _resolve_unique_filename(db: Session, department_id: int, filename: str) -> str:
    """
    If `filename` already exists in this department (but with different
    content — same-content duplicates are rejected before this is ever
    called), appends " (1)", " (2)", ... until it's unique.
    """
    existing_names = {
        row[0] for row in db.query(KnowledgeDocument.filename)
        .filter(KnowledgeDocument.department_id == department_id)
        .all()
    }
    if filename not in existing_names:
        return filename

    base, ext = os.path.splitext(filename)
    counter = 1
    while True:
        candidate = f"{base} ({counter}){ext}"
        if candidate not in existing_names:
            return candidate
        counter += 1


def upload_document(
    db: Session,
    file_bytes: bytes,
    filename: str,
    department_id: int,
    uploaded_by: int
) -> KnowledgeDocument:

    # 1) Extract text FIRST (before touching the DB) so we can check for
    #    duplicate content without ever creating an orphan row.
    print(f"[chatbot] Extracting text from '{filename}' ({len(file_bytes)} bytes)")
    pages = extract_pages(file_bytes, filename)
    print(f"[chatbot] Extracted {len(pages)} page(s)")

    content_hash = _compute_content_hash(pages)

    # 2) Duplicate-content check — regardless of filename. Whether the
    #    incoming file has the SAME name or a DIFFERENT one, if the actual
    #    content already exists in this department it's rejected outright.
    duplicate = (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.department_id == department_id,
            KnowledgeDocument.content_hash == content_hash,
        )
        .first()
    )
    if duplicate:
        print(
            f"[chatbot] Duplicate content detected — matches existing "
            f"document id={duplicate.id} ('{duplicate.filename}')"
        )
        raise ValueError(
            f"This document already exists (uploaded as '{duplicate.filename}')."
        )

    # 3) Same filename but different content → keep both, auto-rename the
    #    new one by appending " (1)", " (2)", etc.
    resolved_filename = _resolve_unique_filename(db, department_id, filename)
    if resolved_filename != filename:
        print(f"[chatbot] Filename '{filename}' already used with different "
              f"content — renaming new upload to '{resolved_filename}'")

    # 4) Record the document now that we know it's not a duplicate
    print(f"[chatbot] Creating KnowledgeDocument row for '{resolved_filename}' in dept {department_id}")
    doc = KnowledgeDocument(
        department_id=department_id,
        filename=resolved_filename,
        content_hash=content_hash,
        uploaded_by=uploaded_by,
        status="uploaded"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    print(f"[chatbot] KnowledgeDocument created with id={doc.id}, status='uploaded'")

    try:
        # 5) Split into chunks, keeping each chunk's page_number
        pieces = chunk_pages(pages)
        print(f"[chatbot] Split into {len(pieces)} chunks")
        if not pieces:
            doc.status = "failed"
            db.commit()
            print(f"[chatbot] No chunks produced — marking as failed")
            return doc

        # 6) Embeddings in one batch
        texts = [p["text"] for p in pieces]
        print(f"[chatbot] Calling HF API to embed {len(texts)} chunks...")
        vectors = embed_chunks(texts)
        print(f"[chatbot] Received {len(vectors)} embedding vectors")

        # 7) Store each chunk with its vector and page number
        for idx, (piece, vector) in enumerate(zip(pieces, vectors)):
            chunk = DocumentChunk(
                document_id=doc.id,
                department_id=department_id,
                chunk_text=piece["text"],
                chunk_index=idx,
                page_number=piece["page_number"],
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
# List documents — powers the Documents page (frontend was calling the
# unrelated app.documents module's /documents endpoint, which reads a
# different table entirely; this is the real listing for the chatbot's
# own knowledge_documents table).
# ---------------------------------------------------------------------------

def list_documents(
    db: Session, department_id: Optional[int]
) -> List[KnowledgeDocument]:
    """
    department_id=None means "no filter" (used for superadmin browsing all
    departments); callers must resolve this server-side the same way
    upload/ask already do — never trust a raw client value for anyone
    other than superadmin.
    """
    query = db.query(KnowledgeDocument).order_by(desc(KnowledgeDocument.created_at))
    if department_id is not None:
        query = query.filter(KnowledgeDocument.department_id == department_id)
    return query.all()


# ---------------------------------------------------------------------------
# Conversations (the sidebar list of separate chat threads)
# ---------------------------------------------------------------------------

MAX_TITLE_CHARS = 60


def _derive_title(first_question: str) -> str:
    text = first_question.strip()
    if len(text) <= MAX_TITLE_CHARS:
        return text
    return text[:MAX_TITLE_CHARS].rstrip() + "…"


def list_conversations(
    db: Session, user_id: int, department_id: int
) -> List[Conversation]:
    return (
        db.query(Conversation)
        .filter(
            Conversation.user_id == user_id,
            Conversation.department_id == department_id,
        )
        .order_by(desc(Conversation.updated_at))
        .all()
    )


def get_conversation(
    db: Session, conversation_id: int, user_id: int
) -> Optional[Conversation]:
    """Scoped to user_id so one agent can never read another's conversation."""
    return (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
        .first()
    )


def delete_conversation(db: Session, conversation_id: int, user_id: int) -> bool:
    convo = get_conversation(db, conversation_id, user_id)
    if not convo:
        return False
    db.delete(convo)
    db.commit()
    return True


def rename_conversation(
    db: Session, conversation_id: int, user_id: int, title: str
) -> Optional[Conversation]:
    convo = get_conversation(db, conversation_id, user_id)
    if not convo:
        return None
    convo.title = title.strip() or convo.title
    db.commit()
    db.refresh(convo)
    return convo


# ---------------------------------------------------------------------------
# Agent question (day 3)
# ---------------------------------------------------------------------------

def ask_question(
    db: Session,
    question: str,
    user: User,
    department_id: int,
    history: Optional[List[ChatHistoryTurn]] = None,
    conversation_id: Optional[int] = None,
) -> dict:
    start = time.time()

    # 0) Resolve (or create) the conversation this turn belongs to. A
    #    conversation_id sent by the client is only trusted after we
    #    confirm it actually belongs to this user — otherwise someone
    #    could append messages into another agent's thread.
    conversation: Optional[Conversation] = None
    if conversation_id is not None:
        conversation = get_conversation(db, conversation_id, user.id)

    if conversation is None:
        conversation = Conversation(
            user_id=user.id,
            department_id=department_id,
            title=_derive_title(question),
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # 1) Embed the question
    query_vector = embed_query(question)

    # 2) Fetch the top K chunks — DEPARTMENT ISOLATION: do not remove.
    #    The department_id is always resolved server-side by the router:
    #    - superadmin: from the explicit request param (validated to exist)
    #    - admin/agent: from the user's own JWT-derived department_id.
    #    Never trust a client-sent value directly — the router enforces this.
    distance_expr = DocumentChunk.embedding_vector.cosine_distance(query_vector)
    stmt = (
        select(DocumentChunk, distance_expr.label("distance"))
        .where(DocumentChunk.department_id == department_id)
        .order_by(distance_expr)
        .limit(TOP_K)
    )

    rows = db.execute(stmt).all()

    # Drop chunks that aren't actually close enough to be relevant. Without
    # this, the top-K is always returned even when nothing in the knowledge
    # base is related to the question, which is what let the model fabricate
    # an answer and still show unrelated documents as its "source".
    top_chunks: List[DocumentChunk] = [
        row.DocumentChunk for row in rows if row.distance <= MAX_RELEVANT_DISTANCE
    ]

    answer = _generate_answer(question, top_chunks, history=history)

    # Only surface a source if the model actually cited it in the answer
    # (greetings, small talk, and "not found in the documents" replies
    # cite nothing and must not show sources — see system_prompt). We
    # don't trust top_chunks alone here: those are everything RETRIEVED
    # and handed to the model as candidate context, not everything it
    # actually used. The model is instructed to cite the filename
    # verbatim, so we check for that.
    used_chunks = [c for c in top_chunks if c.document.filename in answer]

    # One source entry per document actually used (not per chunk), so the
    # same file doesn't show up several times. Page numbers from every
    # relevant chunk of that document are merged into one snippet entry.
    sources = _build_sources(used_chunks)

    latency_ms = int((time.time() - start) * 1000)

    # 3) Audit log — record every question and answer, tied to the conversation
    log = ChatLog(
        conversation_id=conversation.id,
        user_id=user.id,
        department_id=department_id,
        question=question,
        answer=answer,
        source_chunk_ids=",".join(str(c.id) for c in top_chunks),
        latency_ms=latency_ms
    )
    db.add(log)
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(log)

    return {
        "answer": answer,
        "sources": sources,
        "latency_ms": latency_ms,
        "log_id": log.id,
        "conversation_id": conversation.id,
    }


def _build_sources(chunks: List[DocumentChunk]) -> List[SourceSnippet]:
    """
    Collapses chunks into one SourceSnippet per document (not per chunk),
    so the UI doesn't show the same filename repeated several times.
    Uses the highest-ranked (first) chunk of each document for the
    displayed snippet and page number.
    """
    seen_documents: dict[int, DocumentChunk] = {}
    for c in chunks:
        if c.document_id not in seen_documents:
            seen_documents[c.document_id] = c

    return [
        SourceSnippet(
            chunk_id=c.id,
            document_id=c.document_id,
            filename=c.document.filename,
            page_number=c.page_number,
            snippet=c.chunk_text[:200]
        )
        for c in seen_documents.values()
    ]


def _generate_answer(
    question: str,
    chunks: List[DocumentChunk],
    history: Optional[List[ChatHistoryTurn]] = None,
) -> str:
    """
    Builds context from the chunks and asks the LLM for a concise answer
    in the same language as the question. Handles greetings/small talk
    naturally and refuses only when a knowledge-base question has no
    matching content. `chunks` is already filtered to relevant matches
    only (see MAX_RELEVANT_DISTANCE) — if it's empty, no document content
    is available and the model must not pretend otherwise.

    `history` is the recent back-and-forth of THIS conversation (oldest
    first), replayed to the model as real chat turns so it doesn't lose
    context between messages (e.g. "and where does he work?" referring to
    someone named two messages ago). It is NOT re-fetched from documents —
    just previous answers already generated.
    """
    if chunks:
        context_blocks = "\n\n".join(
            f"[Source {i+1} - {c.document.filename}"
            f"{f', page {c.page_number}' if c.page_number else ''}]\n{c.chunk_text}"
            for i, c in enumerate(chunks)
        )
        user_prompt = (
            f"Available information:\n{context_blocks}\n\n"
            f"Question: {question}"
        )
    else:
        user_prompt = (
            "No relevant information was found in the knowledge base for "
            f"this question.\n\nQuestion: {question}"
        )

    system_prompt = (
        "You are a bilingual (Arabic/English) support assistant. Rules:\n"
        "- Detect the language of the user's question and reply ONLY in that "
        "same language. If the question is in Arabic, answer in Arabic. If the "
        "question is in English, answer in English. Never mix languages in a "
        "single answer, and never answer in a language different from the "
        "question's language.\n"
        "- For greetings (like \"ازيك\", \"مرحبا\", \"السلام عليكم\", \"hello\", \"hi\"), "
        "small talk, or general questions unrelated to the uploaded documents — "
        "respond naturally and briefly like a helpful assistant, in the same "
        "language as the user. Do NOT refuse these, and do NOT cite a source "
        "for them.\n"
        "- You may ONLY use facts that literally appear in the 'Available "
        "information' block below. Never use outside knowledge, general "
        "knowledge, or anything you already know about the world — even if "
        "you are confident it's correct — to answer a knowledge-base "
        "question. If it is not written in the provided text, treat it as "
        "unknown.\n"
        "- If the 'Available information' block is empty, or none of it "
        "actually answers the question, say explicitly, in the same "
        "language as the question, that this information is not available "
        "in the uploaded documents. Do not guess, do not fill gaps from "
        "memory, and do not cite a source in this case.\n"
        "- For questions answered using the provided documents: keep the "
        "answer concise and cite the source document name (and page number, "
        "if given) at the end, translated to match the reply language, e.g. "
        "(المصدر: اسم_الملف، صفحة 3) in Arabic or (Source: file_name, page 3) "
        "in English. Only cite a source you actually used to answer."
    )

    messages = [{"role": "system", "content": system_prompt}]

    if history:
        # Only replay the last MAX_HISTORY_TURNS turns to keep token usage
        # bounded on long-running conversations.
        for turn in history[-MAX_HISTORY_TURNS:]:
            role = "assistant" if turn.role == "assistant" else "user"
            messages.append({"role": role, "content": turn.content})

    messages.append({"role": "user", "content": user_prompt})

    response = _get_groq_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2,
    )
    return _strip_thinking(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Conversation history — lets the frontend restore a specific conversation's
# messages on open, and build the `history` list it sends back into
# ask_question above.
# ---------------------------------------------------------------------------

def get_conversation_messages(
    db: Session, conversation_id: int, user_id: int
) -> Optional[List[ChatLog]]:
    """Returns None if the conversation doesn't exist or isn't this user's."""
    conversation = get_conversation(db, conversation_id, user_id)
    if not conversation:
        return None
    return (
        db.query(ChatLog)
        .filter(ChatLog.conversation_id == conversation_id)
        .order_by(ChatLog.created_at)
        .all()
    )


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