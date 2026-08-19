from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


UserRole = Literal["USER", "REVIEWER", "ADMIN"]
VALID_ROLES = {"USER", "REVIEWER", "ADMIN"}


def _normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not normalized or "@" not in normalized or "." not in normalized.split("@")[-1]:
        raise ValueError("Invalid email address.")
    return normalized


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field("USER", min_length=1, max_length=20)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized not in VALID_ROLES:
            raise ValueError(
                f"Invalid role '{value}'. Must be one of: "
                f"{', '.join(sorted(VALID_ROLES))}."
            )
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return _normalize_email(value)


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse