"""Схемы практических заданий."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


TaskType = Literal["code", "theory", "mixed"]


class CheckCriterion(BaseModel):
    criterion: str = Field(min_length=1)
    weight: float = Field(ge=0, le=1)


class TaskPublicForStudent(BaseModel):
    """Условие для студента — БЕЗ reference_solution."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description_md: str
    task_type: TaskType
    language: str | None = None
    requirements: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    passing_score: int
    max_attempts: int
    max_solution_length: int


class TaskFull(BaseModel):
    """Полная схема (для teacher/admin)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description_md: str
    task_type: TaskType
    language: str | None = None
    requirements: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    check_criteria: list[CheckCriterion] = Field(default_factory=list)
    reference_solution: str | None = None
    passing_score: int
    max_attempts: int
    max_solution_length: int
    created_at: datetime


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description_md: str | None = None
    task_type: TaskType | None = None
    language: str | None = None
    requirements: list[str] | None = None
    hints: list[str] | None = None
    check_criteria: list[CheckCriterion] | None = None
    reference_solution: str | None = None
    passing_score: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def check_criteria_weights(self):
        if self.check_criteria is not None:
            total = sum(c.weight for c in self.check_criteria)
            if not (0.99 <= total <= 1.01):
                raise ValueError("Сумма весов критериев должна быть равна 1.0")
        return self
