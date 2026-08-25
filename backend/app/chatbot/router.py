from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.shared.database import get_db
from app.auth.service import require_role
from app.auth.models import User
from app.departments.models import Department

from . import service
from .personas import PERSONAS
from . import nl2sql
from . import voice
from datetime import datetime
from .models import PendingSqlQuery, ChatLog
from .schemas import (
    DocumentUploadOut, ChatQueryIn, ChatQueryOut,
    ChatFeedbackIn, ChatHistoryItem, ConversationOut,
    ConversationDetailOut, ChatWebSearchIn,
    SqlGenerateIn, SqlGenerateOut, SqlExecuteIn, SqlExecuteOut,
    VoiceTranscribeOut, VoiceSpeakIn,
)

router = APIRouter(prefix="", tags=["chatbot"])


@router.get("/chat/personas")
def get_personas(
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    """Powers the persona dropdown in the chat UI."""
    return [
        {"id": key, "label": val["label"]} for key, val in PERSONAS.items()
    ]


@router.post("/chat/documents", response_model=DocumentUploadOut)
async def upload_document(
    file: UploadFile = File(...),
    department_id: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
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
        persona=conversation.persona,
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
            conversation_id=payload.conversation_id, persona=payload.persona,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat query failed: {e}")

    return result


@router.post("/chat/web-search", response_model=ChatQueryOut)
def ask_chatbot_web_search(
    payload: ChatWebSearchIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    """
    Explicit web-search fallback: called only after the normal /chat/query
    answer came back with offer_web_search=True and the user confirmed they
    want it. Never triggered automatically.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is empty")

    if current_user.role == "superadmin":
        if payload.department_id is None:
            raise HTTPException(
                status_code=400,
                detail="Superadmin must specify a department_id",
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
        result = service.web_search_answer(
            db=db, question=payload.question, user=current_user,
            department_id=department_id, conversation_id=payload.conversation_id,
            history=payload.history,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        # e.g. TAVILY_API_KEY not configured
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Web search failed: {e}")

    return result


@router.post("/chat/feedback")
def submit_feedback(
    payload: ChatFeedbackIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    try:
        service.submit_feedback(db=db, log_id=payload.log_id, feedback=payload.feedback)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True}


# ---------------------------------------------------------------------------
# Voice mode (speech-to-text for the mic input, text-to-speech for reading
# answers aloud). Two independent endpoints rather than baking this into
# /chat/query: the recording step and the "please read this answer" step
# don't always happen together (e.g. a restored conversation's messages can
# be replayed without re-transcribing anything), and keeping them separate
# means a TTS failure never blocks the actual chat answer from coming back.
# ---------------------------------------------------------------------------

@router.post("/chat/voice/transcribe", response_model=VoiceTranscribeOut)
async def transcribe_voice_message(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    """Converts a recorded voice message into text for the chat input box."""
    audio_bytes = await file.read()

    try:
        text = voice.transcribe_audio(audio_bytes, filename=file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {e}")

    if not text:
        raise HTTPException(status_code=422, detail="Could not transcribe any speech from the recording")

    return VoiceTranscribeOut(text=text)


@router.post("/chat/voice/speak")
def speak_text(
    payload: VoiceSpeakIn,
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    """Returns narrated WAV audio for a given piece of text (typically an assistant answer)."""
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="No text to speak")

    try:
        audio_bytes = voice.synthesize_speech(payload.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {e}")

    return Response(content=audio_bytes, media_type="audio/wav")


# ---------------------------------------------------------------------------
# NL -> SQL (structured data queries over Wasla's own tickets/users/departments)
# Two steps by design: generate (review-only) then execute (explicit
# approval), and execute only ever runs SQL this backend generated and
# validated itself — never SQL text coming back from the client.
# ---------------------------------------------------------------------------

def _resolve_sql_department_id(
    db: Session, current_user: User, payload_department_id: int | None
) -> int | None:
    if current_user.role == "superadmin":
        # superadmin may leave this unset to query across all departments
        if payload_department_id is not None and not db.get(Department, payload_department_id):
            raise HTTPException(status_code=400, detail=f"department_id {payload_department_id} does not exist")
        return payload_department_id
    department_id = current_user.department_id
    if department_id is None:
        raise HTTPException(status_code=400, detail="Your account is not assigned to any department")
    return department_id


@router.post("/chat/sql/generate", response_model=SqlGenerateOut)
def generate_sql_query(
    payload: SqlGenerateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is empty")

    department_id = _resolve_sql_department_id(db, current_user, payload.department_id)

    try:
        pending = nl2sql.generate_sql(
            db=db, question=payload.question, user=current_user, department_id=department_id
        )
    except nl2sql.SqlValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL generation failed: {e}")

    return SqlGenerateOut(pending_id=pending.id, sql=pending.sql_text, question=pending.question)


@router.post("/chat/sql/execute", response_model=SqlExecuteOut)
def execute_sql_query(
    payload: SqlExecuteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin", "agent")),
):
    pending = db.get(PendingSqlQuery, payload.pending_id)
    if not pending or pending.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="No such pending query")

    try:
        # Re-run the same static validation right before execution too —
        # cheap, and covers the (currently theoretical) case of this row
        # having been tampered with directly in the DB.
        nl2sql.validate_sql(pending.sql_text, user=current_user, department_id=pending.department_id)
        result = nl2sql.execute_sql(db, pending)
    except nl2sql.SqlValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SQL execution failed: {e}")

    log_id = None
    if payload.conversation_id is not None:
        conversation = service.get_conversation(db, payload.conversation_id, current_user.id)
        if conversation:
            preview_rows = result["rows"][:20]
            table_text = " | ".join(result["columns"]) + "\n" + "\n".join(
                " | ".join(str(v) for v in row) for row in preview_rows
            ) if result["rows"] else "لا توجد نتائج."
            answer = f"نتيجة الاستعلام ({result['row_count']} صف):\n\n{table_text}"
            log = ChatLog(
                conversation_id=conversation.id,
                user_id=current_user.id,
                department_id=conversation.department_id,
                question=f"[تنفيذ SQL] {pending.question}",
                answer=answer,
                source_type="sql_result",
            )
            db.add(log)
            conversation.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(log)
            log_id = log.id

    return SqlExecuteOut(**result, log_id=log_id)