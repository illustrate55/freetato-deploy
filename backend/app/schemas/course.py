"""Схемы курсов."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Level = Literal["beginner", "junior", "middle", "senior"]
Status = Literal["draft", "published", "archived"]


class CourseBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None
    category_id: int
    level: Level = "junior"
    target_role: str | None = Field(default=None, max_length=50)
    tags: list[str] = Field(default_factory=list)
    duration_minutes: int = 0
    passing_score: int = Field(default=70, ge=0, le=100)


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    short_description: str | None = None
    description: str | None = None
    category_id: int | None = None
    level: Level | None = None
    target_role: str | None = None
    tags: list[str] | None = None
    duration_minutes: int | None = None
    passing_score: int | None = Field(default=None, ge=0, le=100)


class CoursePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    short_description: str | None = None
    description: str | None = None
    category_id: int
    author_id: int | None = None
    level: Level
    target_role: str | None = None
    tags: list[str] = Field(default_factory=list)
    duration_minutes: int = 0
    status: Status
    enrollment_count: int = 0
    rating_avg: float = 0
    passing_score: int = 70
    lessons_count: int = 0
    modules_count: int = 0
    created_at: datetime
    published_at: datetime | None = None


class CourseListResponse(BaseModel):
    items: list[CoursePublic]
    total: int
    page: int
    page_size: int
