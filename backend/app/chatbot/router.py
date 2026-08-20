from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.auth.service import require_role
from app.auth.models import User
from app.departments.models import Department

from . import service
from .schemas import (
    DocumentUploadOut, ChatQueryIn, ChatQueryOut,
    ChatFeedbackIn, ChatHistoryItem, ConversationOut,
    ConversationDetailOut
)

router = APIRouter(prefix="", tags=["chatbot"])


@router.post("/chat/documents", response_model=DocumentUploadOut)
async def upload_document(
    file: UploadFile = File(...),
    department_id: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin")),
):
    ALLOWED_EXTENSIONS = (
        ".pdf", ".docx",
        ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp",
    )
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail="Only PDF, DOCX, or image files (PNG/JPG/JPEG/BMP/TIFF/WEBP) are allowed",
        )

    # --- Resolve the target department_id based on role ---
    if current_user.role == "superadmin":
        # Superadmin MUST explicitly choose a department.
        if department_id is None:
            raise HTTPException(
                status_code=400,
                detail="Superadmin must specify a department_id",
            )
        # Validate that the department actually exists.
        if not db.get(Department, department_id):
            raise HTTPException(
                status_code=400,
                detail=f"department_id {department_id} does not exist",
            )
    else:
        # Admin: always use their own department — ignore any value the client sent.
        department_id = current_user.department_id
        if department_id is None:
            raise HTTPException(
                status_code=400,
                detail="Your account is not assigned to any department",
            )

    file_bytes = await file.read()
    print(
        f"[chatbot-router] Received file '{file.filename}' "
        f"({len(file_bytes)} bytes) for dept {department_id} "
        f"(uploader role={current_user.role})"
    )

    try:
        doc = service.upload_document(
            db=db,
            file_bytes=file_bytes,
            filename=file.filename,
            department_id=department_id,
            uploaded_by=current_user.id,
        )
    except ValueError as e:
        print(f"[chatbot-router] ValueError: {e}")
        # Duplicate-content uploads get a distinct status code (409) so the
        # frontend can special-case "already exists" vs. a plain bad request.
        status_code = 409 if "already exists" in str(e) else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    except RuntimeError as e:
        print(f"[chatbot-router] RuntimeError: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        print(f"[chatbot-router] Unexpected error: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {e}")

    if doc.status == "failed":
        print(f"[chatbot-router] Document {doc.id} marked as failed")
        raise HTTPException(status_code=422, detail="Failed to extract or process the file")

    print(f"[chatbot-router] Document {doc.id} uploaded successfully (status={doc.status})")
    return doc


@router.get("/chat/documents", response_model=list[DocumentUploadOut])
def get_chatbot_documents(
    department_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    """
    Lists documents from the CHATBOT's own knowledge_documents table (the
    ones actually used for Q&A) — not the unrelated app.documents module.
    """
    if current_user.role == "superadmin":
        # Superadmin may browse one department (?department_id=..) or all.
        if department_id is not None and not db.get(Department, department_id):
            raise HTTPException(
                status_code=400,
                detail=f"department_id {department_id} does not exist",
            )
        resolved_department_id = department_id
    else:
        # Admin/agent always see only their own department — never trust a
        # client-sent value here.
        resolved_department_id = current_user.department_id
        if resolved_department_id is None:
            raise HTTPException(
                status_code=400,
                detail="Your account is not assigned to any department",
            )

    return service.list_documents(db=db, department_id=resolved_department_id)


@router.get("/chat/conversations", response_model=list[ConversationOut])
def get_conversations(
    department_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    """
    Lists this user's chat threads for the sidebar (like ChatGPT/Claude's
    conversation list), most recently active first.
    """
    if current_user.role == "superadmin":
        if department_id is None:
            raise HTTPException(
                status_code=400,
                detail="Superadmin must specify a department_id",
            )
        if not db.get(Department, department_id):
            raise HTTPException(
                status_code=400,
                detail=f"department_id {department_id} does not exist",
            )
        resolved_department_id = department_id
    else:
        resolved_department_id = current_user.department_id
        if resolved_department_id is None:
            raise HTTPException(
                status_code=400,
                detail="Your account is not assigned to any department",
            )

    return service.list_conversations(
        db=db, user_id=current_user.id, department_id=resolved_department_id
    )


@router.get("/chat/conversations/{conversation_id}", response_model=ConversationDetailOut)
def get_conversation_detail(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    """Returns one conversation's full message list, to open it in the panel."""
    conversation = service.get_conversation(db, conversation_id, current_user.id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    logs = service.get_conversation_messages(db, conversation_id, current_user.id)
    return ConversationDetailOut(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        messages=[
            ChatHistoryItem(
                log_id=log.id, question=log.question, answer=log.answer or "",
                feedback=log.feedback, created_at=log.created_at,
            )
            for log in logs
        ],
    )


@router.delete("/chat/conversations/{conversation_id}")
def delete_conversation_endpoint(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    deleted = service.delete_conversation(db, conversation_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}


@router.post("/chat/query", response_model=ChatQueryOut)
def ask_chatbot(
    payload: ChatQueryIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is empty")

    # Resolve the target department: superadmin passes it explicitly, others use their own.
    if current_user.role == "superadmin":
        if payload.department_id is None:
            raise HTTPException(
                status_code=400,
                detail="Superadmin must specify a department_id",
            )
        if not db.get(Department, payload.department_id):
            raise HTTPException(
                status_code=400,
                detail=f"department_id {payload.department_id} does not exist",
            )
        department_id = payload.department_id
    else:
        department_id = current_user.department_id
        if department_id is None:
            raise HTTPException(
                status_code=400,
                detail="Your account is not assigned to any department",
            )

    try:
        result = service.ask_question(
            db=db, question=payload.question, user=current_user,
            department_id=department_id, history=payload.history,
            conversation_id=payload.conversation_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat query failed: {e}")

    return result


@router.post("/chat/feedback")
def submit_feedback(
    payload: ChatFeedbackIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "agent")),
):
    try:
        service.submit_feedback(db=db, log_id=payload.log_id, feedback=payload.feedback)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True}