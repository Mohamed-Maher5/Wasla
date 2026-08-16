# This file defines the request and response shapes for Wasla telephony workflows.
# It keeps calling data consistent between API callers and backend services.

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TriggerCallRequest(BaseModel):
    phone_number: str


class CallAttemptOut(BaseModel):
    id: int
    phone_number: str
    outcome: str | None
    started_at: datetime

    model_config = ConfigDict(from_attributes=True)
