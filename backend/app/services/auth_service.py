"""Логика регистрации, логина и refresh-rotation."""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.models.category import Category
from app.models.user import User
from app.schemas.auth import RegisterRequest


async def register_user(db: AsyncSession, payload: RegisterRequest) -> User:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_TAKEN", "message": "Пользователь с таким email уже существует"},
        )

    # Для студента проверяем, что все указанные направления существуют.
    # Преподаватель регистрируется без программы обучения — пропускаем проверку.
    if payload.role == "student" and payload.directions:
        cats = await db.execute(select(Category.id).where(Category.id.in_(payload.directions)))
        found_ids = {row[0] for row in cats.all()}
        missing = [d for d in payload.directions if d not in found_ids]
        if missing:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_DIRECTIONS", "message": f"Направления не найдены: {missing}"},
            )

    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        role=payload.role,
        directions=payload.directions,
        current_level=payload.current_level,
        target_level=payload.target_level,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    user = (
        await db.execute(select(User).where(User.email == email.lower()))
    ).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Неверный email или пароль"},
        )
    if user.is_blocked or not user.is_active:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_BLOCKED", "message": "Учётная запись заблокирована"},
        )
    return user


async def issue_token_pair(db: AsyncSession, user: User) -> tuple[str, str]:
    access = create_access_token(user.id, user.role)
    refresh = create_refresh_token(user.id)
    new_hash = hash_refresh_token(refresh)
    now = datetime.now(timezone.utc)
    # Явный UPDATE: ORM dirty-tracking иногда не отрабатывает после select+attr-set.
    await db.execute(
        update(User)
        .where(User.id == user.id)
        .values(refresh_token_hash=new_hash, last_login_at=now)
    )
    await db.commit()
    user.refresh_token_hash = new_hash
    user.last_login_at = now
    return access, refresh


async def rotate_refresh(db: AsyncSession, user: User, refresh_token: str) -> tuple[str, str]:
    stored = user.refresh_token_hash
    if not stored or not verify_refresh_token(refresh_token, stored):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_REFRESH", "message": "Невалидный refresh-токен"},
        )
    return await issue_token_pair(db, user)


async def logout(db: AsyncSession, user: User) -> None:
    user.refresh_token_hash = None
    await db.commit()


async def change_password(db: AsyncSession, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CURRENT_PASSWORD", "message": "Текущий пароль неверен"},
        )
    user.password_hash = hash_password(new)
    user.refresh_token_hash = None
    await db.commit()
