# This file exposes department endpoints for the Wasla backend.
# It is the HTTP boundary for managing and reading company department data.

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import get_current_user, require_role
from app.departments.schemas import DepartmentCreate, DepartmentOut
from app.departments.service import create_department, list_departments
from app.shared.database import get_db


router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentOut])
def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DepartmentOut]:
    return list_departments(db, current_user)


@router.post("", response_model=DepartmentOut)
def post_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin")),
) -> DepartmentOut:
    return create_department(data, db, current_user)
