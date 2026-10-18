"""Урок: text / quiz / task."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    module_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    content_html: Mapped[str | None] = mapped_column(nullable=True)
    content_markdown: Mapped[str | None] = mapped_column(nullable=True)
    quiz_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True
    )
    task_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    module = relationship("Module", back_populates="lessons")
    quiz = relationship("Quiz", foreign_keys=[quiz_id])
    task = relationship("Task", foreign_keys=[task_id])

    __table_args__ = (
        CheckConstraint("type IN ('text','quiz','task')", name="lessons_type_check"),
        Index("ix_lessons_module_sort", "module_id", "sort_order"),
    )
