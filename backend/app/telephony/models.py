# This file describes the persisted telephony data used by Wasla.
# It belongs to the backend calling layer that tracks outreach and verification results.

from sqlalchemy import Column, DateTime, Integer, String

from app.shared.database import Base


class CallAttempt(Base):
    __tablename__ = "call_attempts"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, nullable=False)
    conversation_uuid = Column(String, nullable=True)
    transcript = Column(String, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    outcome = Column(String, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
