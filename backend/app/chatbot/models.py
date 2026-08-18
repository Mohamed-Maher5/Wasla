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
    embedding_vector = Column(Vector(EMBEDDING_DIM), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
 
    document = relationship("KnowledgeDocument", back_populates="chunks")
 
 
class ChatLog(Base):
    """
    Audit trail: every question and answer — required by use case 2
    (access control & audit trail). Not part of the base 3-day plan,
    but added from the start so the foundation is correct.
    """
    __tablename__ = "chat_logs"
 
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    source_chunk_ids = Column(String(255), nullable=True)  # e.g. "12,45,9"
    latency_ms = Column(Integer, nullable=True)
    feedback = Column(String(20), nullable=True)  # "up" / "down" / null
    created_at = Column(DateTime, default=datetime.utcnow)
 