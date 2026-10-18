"""Схемы пользователей."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


CurrentLevel = Literal["beginner", "junior", "middle"]
TargetLevel = Literal["junior", "middle", "senior"]
Role = Literal["student", "teacher", "admin"]

LEVEL_ORDER = {"beginner": 0, "junior": 1, "middle": 2, "senior": 3}


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str
    last_name: str
    position: str | None = None
    role: Role
    bio: str | None = None
    phone: str | None = None
    directions: list[int] = Field(default_factory=list)
    current_level: CurrentLevel | None = None
    target_level: TargetLevel | None = None
    is_active: bool = True
    is_blocked: bool = False
    created_at: datetime
    last_login_at: datetime | None = None


class UserUpdateMe(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    position: str | None = Field(default=None, max_length=150)
    bio: str | None = None
    phone: str | None = Field(default=None, max_length=50)
    directions: list[int] | None = None
    current_level: CurrentLevel | None = None
    target_level: TargetLevel | None = None

    @model_validator(mode="after")
    def check_level_order(self):
        if self.current_level and self.target_level:
            if LEVEL_ORDER[self.target_level] < LEVEL_ORDER[self.current_level]:
                raise ValueError("Желаемый уровень не может быть ниже текущего")
        return self


class UserCreateAdmin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: Role = "student"
    position: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return (v or "").strip().lower()


class UserUpdateAdmin(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    position: str | None = None
    is_active: bool | None = None
    is_blocked: bool | None = None


class RoleChange(BaseModel):
    role: Role


class UserStats(BaseModel):
    active_courses: int
    completed_courses: int


class ChangePassword(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class UserListResponse(BaseModel):
    items: list[UserPublic]
    total: int
    page: int
    page_size: int
