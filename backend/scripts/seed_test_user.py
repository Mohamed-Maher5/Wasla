from app.auth.models import User
from app.auth.service import hash_password
from app.departments.models import Department  # noqa: F401
from app.shared.database import Base, SessionLocal, engine
from app.telephony.models import CallAttempt  # noqa: F401
from app.tickets.models import Ticket  # noqa: F401


SUPERADMIN_EMAIL = "super-admin@gmail.com"


def main() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.email == SUPERADMIN_EMAIL).first()
        if existing_user is not None:
            print(f"Superadmin {SUPERADMIN_EMAIL} already exists; skipping insert.")
            return

        user = User(
            name="superadmin",
            email=SUPERADMIN_EMAIL,
            password_hash=hash_password("1234"),
            role="superadmin",
            department_id=None,
        )
        db.add(user)
        db.commit()
        print(f"Created superadmin {SUPERADMIN_EMAIL}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
