"""Схемы аутентификации."""
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas.user import (
    LEVEL_ORDER,
    CurrentLevel,
    TargetLevel,
    UserPublic,
)


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return _normalize_email(v)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"] = "Bearer"
    user: UserPublic


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"] = "Bearer"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: Literal["student", "teacher"] = "student"
    directions: list[int] = Field(default_factory=list)
    current_level: CurrentLevel | None = None
    target_level: TargetLevel | None = None

    @field_validator("email", mode="before")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return _normalize_email(v)

    @model_validator(mode="after")
    def check_payload(self):
        if self.role == "student":
            if not self.directions:
                raise ValueError("Нужно выбрать хотя бы одно направление")
            if self.current_level is None or self.target_level is None:
                raise ValueError("Для студента укажите текущий и желаемый уровни")
            if LEVEL_ORDER[self.target_level] < LEVEL_ORDER[self.current_level]:
                raise ValueError("Желаемый уровень не может быть ниже текущего")
        else:
            # Преподаватель регистрируется без программы обучения
            self.directions = []
            self.current_level = None
            self.target_level = None
        return self
