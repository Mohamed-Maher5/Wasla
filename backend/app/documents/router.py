from fastapi import APIRouter, Depends, Form, UploadFile
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import get_current_user, require_role
from app.documents.schemas import DocumentOut
from app.documents.service import list_documents, upload_document
from app.shared.database import get_db


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DocumentOut]:
    return list_documents(db, current_user)


@router.post("", response_model=DocumentOut)
def post_document(
    file: UploadFile,
    department_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> DocumentOut:
    return upload_document(file, db, current_user, department_id)
