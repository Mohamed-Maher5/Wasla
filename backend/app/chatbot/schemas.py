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
    persona: str = "general"  # only applied when this call starts a NEW conversation;
                               # ignored for an existing conversation_id (persona is fixed
                               # per-conversation — see chatbot/personas.py)
 
 
class SourceSnippet(BaseModel):
    source_type: str = "document"  # "document" or "web"
    chunk_id: Optional[int] = None
    document_id: Optional[int] = None
    filename: Optional[str] = None
    page_number: Optional[int] = None  # 1-based PDF page; None for DOCX or unknown
    snippet: str  # first 200 chars of the chunk (or web result), so the agent can preview the source
    url: Optional[str] = None  # set only for source_type == "web"
    title: Optional[str] = None  # set only for source_type == "web"


class SqlPreview(BaseModel):
    pending_id: int
    sql: str


class ChatQueryOut(BaseModel):
    answer: str
    sources: List[SourceSnippet]
    latency_ms: int
    log_id: int  # so feedback can update the same record
    conversation_id: int  # echoed back so the frontend can keep using it for the next message
    offer_web_search: bool = False  # True when nothing relevant was found in the docs and the
                                     # frontend should ask the user whether to search the web
    sql_query: Optional[SqlPreview] = None  # set when the question was routed to structured
                                             # data instead of document RAG — frontend renders
                                             # the SQL preview + an "execute" button inline


class ChatWebSearchIn(BaseModel):
    """Sent when the user confirms they want the web-search fallback for their last question."""
    question: str
    department_id: int | None = None
    history: List[ChatHistoryTurn] = []
    conversation_id: int  # the conversation the original question belongs to


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
    persona: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationDetailOut(BaseModel):
    id: int
    title: str
    persona: str
    created_at: datetime
    messages: List[ChatHistoryItem]
 
 
# ---------- Feedback ----------
 
class ChatFeedbackIn(BaseModel):
    log_id: int
    feedback: str  # "up" or "down"


# ---------- NL -> SQL (structured data queries) ----------

class SqlGenerateIn(BaseModel):
    question: str
    department_id: int | None = None  # superadmin passes this explicitly


class SqlGenerateOut(BaseModel):
    pending_id: int
    sql: str
    question: str


class SqlExecuteIn(BaseModel):
    pending_id: int
    conversation_id: int | None = None  # when set, the result is also logged into this
                                         # conversation's history like a normal chat turn


class SqlExecuteOut(BaseModel):
    sql: str
    columns: List[str]
    rows: List[List[object]]
    row_count: int
    log_id: int | None = None  # set when conversation_id was provided and the result was logged


# ---------- Voice (speech-to-text / text-to-speech) ----------

class VoiceTranscribeOut(BaseModel):
    text: str  # transcribed text — frontend drops this into the chat input


class VoiceSpeakIn(BaseModel):
    text: str  # usually the assistant's answer text, sent back for narration