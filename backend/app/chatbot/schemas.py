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
 
class ChatQueryIn(BaseModel):
    question: str
 
 
class SourceSnippet(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    snippet: str  # first 200 chars of the chunk, so the agent can see the answer's source
 
 
class ChatQueryOut(BaseModel):
    answer: str
    sources: List[SourceSnippet]
    latency_ms: int
    log_id: int  # so feedback can update the same record
 
 
# ---------- Feedback ----------
 
class ChatFeedbackIn(BaseModel):
    log_id: int
    feedback: str  # "up" or "down"
 