# This file describes the persisted department data used by Wasla.
# It belongs to the backend company-structure layer that separates teams and responsibilities.

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from app.shared.database import Base


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
