"""Схемы сдач практических заданий."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SubmissionStatus = Literal["pending", "checking", "checked", "error"]


class SubmissionCreate(BaseModel):
    solution: str = Field(min_length=1, max_length=20000)


class CriterionResult(BaseModel):
    criterion: str
    score: float
    comment: str | None = None


class SubmissionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    task_id: int
    status: SubmissionStatus
    score_percent: int | None = None
    is_passed: bool = False
    solution: str | None = None
    ai_summary: str | None = None
    ai_per_criterion: list[CriterionResult] | None = None
    ai_improvement_tips: list[str] | None = None
    error_message: str | None = None
    submitted_at: datetime
    checked_at: datetime | None = None


class SubmissionListResponse(BaseModel):
    items: list[SubmissionPublic]
    total: int


class SubmissionAccepted(BaseModel):
    """Ответ 202 на POST /tasks/{id}/submissions."""
    submission_id: int
    status: SubmissionStatus = "pending"
