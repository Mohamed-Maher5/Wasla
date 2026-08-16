# This file defines the request and response shapes for Wasla authentication.
# It keeps the API contract for identity flows clear at the backend boundary.

from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    department_id: int | None

    model_config = ConfigDict(from_attributes=True)
