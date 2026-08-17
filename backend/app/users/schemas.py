from typing import Literal

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: Literal["admin", "agent"]
    department_id: int


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    department_id: int | None

    model_config = ConfigDict(from_attributes=True)
