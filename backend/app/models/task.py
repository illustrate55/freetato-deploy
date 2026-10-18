"""Практические задания. Проверяются ИИ по check_criteria."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description_md: Mapped[str] = mapped_column(nullable=False)
    task_type: Mapped[str] = mapped_column(String(20), nullable=False, default="code", server_default="code")
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    hints: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    check_criteria: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    reference_solution: Mapped[str | None] = mapped_column(nullable=True)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    passing_score: Mapped[int] = mapped_column(Integer, nullable=False, default=70, server_default="70")
    max_solution_length: Mapped[int] = mapped_column(
        Integer, nullable=False, default=10000, server_default="10000"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint("task_type IN ('code','theory','mixed')", name="tasks_task_type_check"),
    )
