# This file defines the request and response shapes for Wasla tickets.
# It keeps ticket data consistent between API callers and backend logic.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.shared.constants import TicketStatus


class TicketCreate(BaseModel):
    client_name: str
    client_phone_number: str
    description: str
    assigned_to: int
    department_id: int


class TicketStatusUpdate(BaseModel):
    status: Literal[TicketStatus.RESOLVED.value, TicketStatus.UNRESOLVED.value]


class TicketOut(BaseModel):
    id: str
    client_name: str
    client_phone_number: str
    description: str
    assigned_to: int
    status: str
    department_id: int
    created_by: int | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
