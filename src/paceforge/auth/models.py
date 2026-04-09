"""Pydantic request / response models for authentication."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    reason: str = Field("", max_length=500)


class AppLoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
    reason: str
    created_at: str
    approved_at: str | None = None
    garmin_email: str | None = None


class UserStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(approved|rejected)$")
