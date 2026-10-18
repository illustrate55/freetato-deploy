"""Модули внутри курса."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    course_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    course = relationship("Course", back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Lesson.sort_order",
    )

    __table_args__ = (Index("ix_modules_course_sort", "course_id", "sort_order"),)
