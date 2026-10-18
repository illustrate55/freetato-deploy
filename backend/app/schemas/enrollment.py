"""Схемы записей на курсы и прогресса."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EnrollmentStatus = Literal["active", "completed", "dropped"]


class EnrollmentCreate(BaseModel):
    course_id: int


class EnrollmentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    course_id: int
    course_title: str | None = None
    course_category_id: int | None = None
    status: EnrollmentStatus
    progress_percent: int
    enrolled_at: datetime
    completed_at: datetime | None = None
    last_lesson_id: int | None = None
    lessons_total: int = 0
    lessons_completed: int = 0


class EnrollmentProgress(BaseModel):
    enrollment_id: int
    course_id: int
    course_title: str
    progress_percent: int
    lessons_total: int
    lessons_completed: int
    status: EnrollmentStatus
    last_lesson_id: int | None = None
    lessons_status: dict[str, str] = Field(default_factory=dict)


class EnrollmentListResponse(BaseModel):
    items: list[EnrollmentPublic]
    total: int
