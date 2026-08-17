# This file holds the business logic for Wasla documents.
# It coordinates file storage and department-scoped document visibility.

import shutil
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.departments.models import Department
from app.documents.models import Document
from app.shared.constants import UserRole

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def upload_document(
    file: UploadFile,
    db: Session,
    current_user: User,
    department_id: int,
) -> Document:
    if current_user.role == UserRole.ADMIN.value:
        if current_user.department_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin must belong to a department to upload documents",
            )
        if department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins can only upload documents to their own department",
            )
    elif current_user.role == UserRole.SUPERADMIN.value:
        if db.query(Department).filter(Department.id == department_id).first() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="department_id must reference an existing department",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and superadmins can upload documents",
        )

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{suffix}' is not allowed. Use PDF or DOCX.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    document = Document(
        filename=file.filename,
        department_id=department_id,
        uploaded_by=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session, current_user: User) -> list[Document]:
    query = db.query(Document)

    if current_user.role == UserRole.SUPERADMIN.value:
        return query.order_by(Document.uploaded_at.desc()).all()

    if current_user.role in {UserRole.ADMIN.value, UserRole.AGENT.value}:
        if current_user.department_id is None:
            return []
        return (
            query.filter(Document.department_id == current_user.department_id)
            .order_by(Document.uploaded_at.desc())
            .all()
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to view documents",
    )
