"""Schemas de autenticação e usuários."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: UserRole
    professional_id: int | None = None
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    professional_id: int | None = None


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=3, max_length=120)
    role: UserRole | None = None
    is_active: bool | None = None
    professional_id: int | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class LoginEvent(BaseModel):
    at: datetime | None = None
