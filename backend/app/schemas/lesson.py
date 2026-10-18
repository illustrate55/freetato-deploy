"""Схемы уроков."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


LessonType = Literal["text", "quiz", "task"]


class LessonCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: LessonType
    content_markdown: str | None = None
    duration_minutes: int = 0
    sort_order: int = 0
    is_required: bool = True


class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content_markdown: str | None = None
    duration_minutes: int | None = None
    sort_order: int | None = None
    is_required: bool | None = None


class LessonPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    module_id: int
    title: str
    type: LessonType
    sort_order: int
    duration_minutes: int = 0
    content_markdown: str | None = None
    quiz_id: int | None = None
    task_id: int | None = None
    is_required: bool = True
    created_at: datetime
