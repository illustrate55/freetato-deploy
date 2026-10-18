"""Админ-эндпоинты: статистика."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_role
from app.models.ai_usage import AIUsage
from app.models.attempt import QuizAttempt
from app.models.course import Course
from app.models.user import User

router = APIRouter()


class AdminStats(BaseModel):
    users_total: int
    users_students: int
    users_teachers: int
    users_admins: int
    courses_total: int
    courses_published: int
    quiz_attempts_total: int
    ai_tokens_month: int


class TimeSeriesPoint(BaseModel):
    date: str
    value: int


class TimeSeriesResponse(BaseModel):
    items: list[TimeSeriesPoint]


@router.get("/stats", response_model=AdminStats, summary="Сводная статистика")
async def get_stats(
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AdminStats:
    users_total = (await db.execute(select(func.count(User.id)))).scalar() or 0
    students = (await db.execute(select(func.count(User.id)).where(User.role == "student"))).scalar() or 0
    teachers = (await db.execute(select(func.count(User.id)).where(User.role == "teacher"))).scalar() or 0
    admins = (await db.execute(select(func.count(User.id)).where(User.role == "admin"))).scalar() or 0
    courses_total = (await db.execute(select(func.count(Course.id)))).scalar() or 0
    published = (await db.execute(select(func.count(Course.id)).where(Course.status == "published"))).scalar() or 0
    attempts = (await db.execute(select(func.count(QuizAttempt.id)))).scalar() or 0

    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    tokens_month = (
        await db.execute(
            select(func.coalesce(func.sum(AIUsage.tokens_used), 0)).where(AIUsage.created_at >= month_ago)
        )
    ).scalar() or 0

    return AdminStats(
        users_total=int(users_total),
        users_students=int(students),
        users_teachers=int(teachers),
        users_admins=int(admins),
        courses_total=int(courses_total),
        courses_published=int(published),
        quiz_attempts_total=int(attempts),
        ai_tokens_month=int(tokens_month),
    )


@router.get(
    "/stats/registrations",
    response_model=TimeSeriesResponse,
    summary="Регистрации по дням",
)
async def registrations(
    days: int = Query(default=30, ge=1, le=365),
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> TimeSeriesResponse:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await db.execute(
            select(func.date_trunc("day", User.created_at).label("d"), func.count(User.id))
            .where(User.created_at >= since)
            .group_by("d")
            .order_by("d")
        )
    ).all()
    items = [
        TimeSeriesPoint(date=r[0].date().isoformat() if hasattr(r[0], "date") else str(r[0]), value=int(r[1]))
        for r in rows
    ]
    return TimeSeriesResponse(items=items)


@router.get("/stats/ai-usage", response_model=TimeSeriesResponse, summary="Расход ИИ-токенов по дням")
async def ai_usage_stats(
    days: int = Query(default=30, ge=1, le=365),
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> TimeSeriesResponse:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        await db.execute(
            select(
                func.date_trunc("day", AIUsage.created_at).label("d"),
                func.coalesce(func.sum(AIUsage.tokens_used), 0),
            )
            .where(AIUsage.created_at >= since)
            .group_by("d")
            .order_by("d")
        )
    ).all()
    items = [
        TimeSeriesPoint(date=r[0].date().isoformat() if hasattr(r[0], "date") else str(r[0]), value=int(r[1]))
        for r in rows
    ]
    return TimeSeriesResponse(items=items)
