from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.models import User
from app.auth.service import get_current_user, hash_password, require_role
from app.departments.models import Department
from app.shared.constants import UserRole
from app.shared.database import get_db
from app.users.schemas import UserCreate, UserOut


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[User]:
    if current_user.role == UserRole.SUPERADMIN.value:
        return db.query(User).order_by(User.id).all()

    if current_user.role == UserRole.ADMIN.value:
        if current_user.department_id is None:
            return []
        return (
            db.query(User)
            .filter(User.department_id == current_user.department_id)
            .order_by(User.id)
            .all()
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to view users",
    )


@router.post("", response_model=UserOut)
def post_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("superadmin", "admin")),
) -> User:
    department = db.get(Department, data.department_id)
    if department is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="department_id must reference an existing department",
        )

    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email already exists",
        )

    if current_user.role == UserRole.ADMIN.value:
        if data.department_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins can only create users in their own department",
            )
        if data.role != UserRole.AGENT.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admins can only create agents",
            )

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        department_id=data.department_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
