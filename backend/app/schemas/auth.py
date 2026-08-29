from pydantic import BaseModel, Field
from typing import Literal


class SignupRequest(BaseModel):
    role: Literal["farmer", "officer"]
    full_name: str = Field(min_length=2, max_length=100)
    phone_number: str = Field(min_length=10, max_length=15)
    email: str | None = None
    password: str = Field(min_length=6)


class LoginRequest(BaseModel):
    phone_number: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
