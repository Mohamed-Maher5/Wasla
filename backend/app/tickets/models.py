# This file describes the persisted support ticket data used by Wasla.
# It belongs to the backend ticketing layer that tracks customer problems and outcomes.

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String

from app.shared.constants import TicketStatus
from app.shared.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(6), primary_key=True, index=True)
    client_name = Column(String, nullable=False)
    client_phone_number = Column(String, nullable=False)
    description = Column(String, nullable=False)
    assigned_to = Column(ForeignKey("users.id"), nullable=False)
    department_id = Column(ForeignKey("departments.id"), nullable=False)
    status = Column(String, nullable=False, default=TicketStatus.UNRESOLVED.value)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
