"""Схемы категорий-направлений."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    icon_name: str | None = None
    sort_order: int
    created_at: datetime


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=120)
    icon_name: str | None = Field(default=None, max_length=50)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    icon_name: str | None = None
    sort_order: int | None = None
