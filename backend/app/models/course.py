"""Курсы. Привязаны к категории-направлению, имеют level и status."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(nullable=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    author_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="junior", server_default="junior")
    target_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft", server_default="draft")
    enrollment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rating_avg: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0, server_default="0")
    passing_score: Mapped[int] = mapped_column(Integer, nullable=False, default=70, server_default="70")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    modules: Mapped[list["Module"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.sort_order",
    )

    __table_args__ = (
        CheckConstraint("level IN ('beginner','junior','middle','senior')", name="courses_level_check"),
        CheckConstraint("status IN ('draft','published','archived')", name="courses_status_check"),
        Index("ix_courses_status", "status"),
        Index("ix_courses_category_level", "category_id", "level"),
        Index("ix_courses_author", "author_id"),
    )
