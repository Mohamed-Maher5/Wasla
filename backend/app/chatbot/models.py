import uuid
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
 

from app.shared.database import Base
 
EMBEDDING_DIM = 384
 
 
class KnowledgeDocument(Base):
    """
    An uploaded file (PDF / DOCX) before it's split into chunks.
    """
    __tablename__ = "knowledge_documents"
 
    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_hash = Column(String(64), nullable=True, index=True)  # sha256 of extracted text — used for duplicate detection
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="uploaded")  # uploaded / chunked / embedded / failed
    created_at = Column(DateTime, default=datetime.utcnow)
 
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
 
 
class DocumentChunk(Base):
    """
    A text chunk from a document + its embedding.
    department_id is intentionally denormalized here so filtering at
    query time is fast, without needing a join to KnowledgeDocument
    every time.
    """
    __tablename__ = "document_chunks"
 
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # order of this chunk within the document
    page_number = Column(Integer, nullable=True)  # 1-based PDF page; null for DOCX (no page concept)
    embedding_vector = Column(Vector(EMBEDDING_DIM), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
 
    document = relationship("KnowledgeDocument", back_populates="chunks")
 
 
class Conversation(Base):
    """
    A single chat thread ("محادثة") — the unit the sidebar lists. Each
    ChatLog (one question+answer turn) belongs to exactly one conversation.
    `title` is auto-derived from the first question (truncated), like most
    chat UIs, and can be renamed later.
    """
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="محادثة جديدة")
    persona = Column(String(30), nullable=False, default="general")  # see chatbot/personas.py
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    logs = relationship(
        "ChatLog",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatLog.created_at",
    )


class ChatLog(Base):
    """
    Audit trail: every question and answer — required by use case 2
    (access control & audit trail). Not part of the base 3-day plan,
    but added from the start so the foundation is correct.
    """
    __tablename__ = "chat_logs"
 
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    source_chunk_ids = Column(String(255), nullable=True)  # e.g. "12,45,9"
    source_type = Column(String(20), nullable=False, default="document")  # "document" or "web"
    web_sources = Column(Text, nullable=True)  # JSON list of {"title","url"} when source_type="web"
    latency_ms = Column(Integer, nullable=True)
    feedback = Column(String(20), nullable=True)  # "up" / "down" / null
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="logs")


class PendingSqlQuery(Base):
    """
    A generated-but-not-yet-executed NL->SQL query, awaiting user approval.
    Storing it server-side (instead of round-tripping the SQL text through
    the client) means the /chat/sql/execute endpoint only ever runs SQL
    this backend itself generated and validated — a client can't submit
    arbitrary SQL by editing the approval request.
    """
    __tablename__ = "pending_sql_queries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    question = Column(Text, nullable=False)
    sql_text = Column(Text, nullable=False)
    executed = Column(String(1), nullable=False, default="0")  # "0"/"1" — one-shot execute guard
    created_at = Column(DateTime, default=datetime.utcnow)