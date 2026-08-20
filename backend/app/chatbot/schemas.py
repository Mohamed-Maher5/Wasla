from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
 
 
# ---------- Document upload ----------
 
class DocumentUploadOut(BaseModel):
    id: int
    filename: str
    department_id: int
    status: str
    created_at: datetime
 
    class Config:
        from_attributes = True
 
 
# ---------- Question ----------
 
class ChatHistoryTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatQueryIn(BaseModel):
    question: str
    department_id: int | None = None  # superadmin passes this explicitly
    history: List[ChatHistoryTurn] = []  # recent prior turns of THIS conversation, oldest first
    conversation_id: int | None = None  # None = start a brand-new conversation
 
 
class SourceSnippet(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    page_number: Optional[int] = None  # 1-based PDF page; None for DOCX or unknown
    snippet: str  # first 200 chars of the chunk, so the agent can see the answer's source
 
 
class ChatQueryOut(BaseModel):
    answer: str
    sources: List[SourceSnippet]
    latency_ms: int
    log_id: int  # so feedback can update the same record
    conversation_id: int  # echoed back so the frontend can keep using it for the next message


# ---------- Chat history (used to restore a conversation on page load) ----------

class ChatHistoryItem(BaseModel):
    log_id: int
    question: str
    answer: str
    feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Conversations (the sidebar list) ----------

class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    messages: List[ChatHistoryItem]
 
 
# ---------- Feedback ----------
 
class ChatFeedbackIn(BaseModel):
    log_id: int
    feedback: str  # "up" or "down"