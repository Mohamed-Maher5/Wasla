from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
 
from app.shared.database import get_db
from app.auth.service import get_current_user
from app.auth.models import User
 
from . import service
from .schemas import (
    DocumentUploadOut, ChatQueryIn, ChatQueryOut,
    ChatFeedbackIn
)
 
router = APIRouter(prefix="", tags=["chatbot"])
 
 
@router.post("/departments/{department_id}/documents", response_model=DocumentUploadOut)
async def upload_document(
    department_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith((".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Only PDF or DOCX allowed")
 
    file_bytes = await file.read()
 
    try:
        doc = service.upload_document(
            db=db,
            file_bytes=file_bytes,
            filename=file.filename,
            department_id=department_id,
            uploaded_by=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
 
    if doc.status == "failed":
        raise HTTPException(status_code=422, detail="Failed to extract or process the file")
 
    return doc
 
 
@router.post("/chat/query", response_model=ChatQueryOut)
def ask_chatbot(
    payload: ChatQueryIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is empty")
 
    result = service.ask_question(db=db, question=payload.question, user=current_user)
    return result
 
 
@router.post("/chat/feedback")
def submit_feedback(
    payload: ChatFeedbackIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        service.submit_feedback(db=db, log_id=payload.log_id, feedback=payload.feedback)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
 
    return {"ok": True}
 