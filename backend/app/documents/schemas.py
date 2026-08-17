# This file defines the response shape for Wasla documents.
# It keeps document data consistent between API callers and backend logic.

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    id: int
    filename: str
    department_id: int
    uploaded_by: int
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)
