"""Сдачи практических заданий студентами + результат ИИ-проверки."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    enrollment_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False
    )
    solution: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(
        nullable=False, default="pending", server_default="pending"
    )
    score_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    ai_summary: Mapped[str | None] = mapped_column(nullable=True)
    ai_per_criterion: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    ai_improvement_tips: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','checking','checked','error')",
            name="submissions_status_check",
        ),
        Index("ix_submissions_user_status", "user_id", "status"),
        Index("ix_submissions_task", "task_id"),
    )
