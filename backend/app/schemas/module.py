"""Схемы модулей и структуры курса."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


LessonType = Literal["text", "quiz", "task"]


class LessonInModule(BaseModel):
    """Урок в карточке модуля — без полного контента."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    type: LessonType
    sort_order: int
    duration_minutes: int = 0
    is_required: bool = True


class ModulePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    description: str | None = None
    sort_order: int
    lessons: list[LessonInModule] = Field(default_factory=list)
    created_at: datetime


class ModuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    sort_order: int = 0


class ModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    sort_order: int | None = None
