# This file holds the business logic for Wasla departments.
# It coordinates department behavior used by support, access control, and knowledge workflows.

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.departments.models import Department
from app.departments.schemas import DepartmentCreate
from app.shared.constants import UserRole


def list_departments(db: Session, current_user: User) -> list[Department]:
    query = db.query(Department)

    if current_user.role == UserRole.SUPERADMIN.value:
        return query.order_by(Department.id).all()

    if current_user.role in {UserRole.ADMIN.value, UserRole.AGENT.value}:
        if current_user.department_id is None:
            return []
        return (
            query.filter(Department.id == current_user.department_id)
            .order_by(Department.id)
            .all()
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to view departments",
    )


def create_department(data: DepartmentCreate, db: Session, current_user: User) -> Department:
    if current_user.role != UserRole.SUPERADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmins can create departments",
        )

    department = Department(name=data.name, description=data.description)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department
