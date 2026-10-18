"""Пользователи. Для роли student хранится профиль обучения."""
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str | None] = mapped_column(String(150), nullable=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student", server_default="student")
    bio: Mapped[str | None] = mapped_column(nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Профиль обучения (только для student)
    directions: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list, server_default="[]")
    current_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    target_level: Mapped[str | None] = mapped_column(String(20), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint("role IN ('student','teacher','admin')", name="users_role_check"),
        CheckConstraint(
            "current_level IS NULL OR current_level IN ('beginner','junior','middle')",
            name="users_current_level_check",
        ),
        CheckConstraint(
            "target_level IS NULL OR target_level IN ('junior','middle','senior')",
            name="users_target_level_check",
        ),
        Index("ix_users_role", "role"),
        Index("ix_users_directions", "directions", postgresql_using="gin"),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
