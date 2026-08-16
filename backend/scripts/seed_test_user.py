from sqlalchemy import Column, Integer, Table

from app.auth.models import User
from app.auth.service import hash_password
from app.shared.database import Base, SessionLocal, engine


TEST_USER_EMAIL = "test@wasla.com"


Table(
    "departments",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    extend_existing=True,
)


def main() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == TEST_USER_EMAIL).first()
        if existing_user is not None:
            print(f"Test user {TEST_USER_EMAIL} already exists; skipping insert.")
            return

        user = User(
            name="Test User",
            email=TEST_USER_EMAIL,
            password_hash=hash_password("test123"),
            role="superadmin",
            department_id=None,
        )
        db.add(user)
        db.commit()
        print(f"Created test user {TEST_USER_EMAIL}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
