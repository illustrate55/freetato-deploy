"""Бизнес-логика курсов: фильтрация по профилю студента и проверка доступа."""
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import LEVELS_LE
from app.models.course import Course
from app.models.user import User


def build_courses_query(
    user: User,
    search: str | None = None,
    level: str | None = None,
    category_id: int | None = None,
    status_filter: str | None = None,
) -> Select:
    """Строит SELECT с автоматической фильтрацией под профиль студента."""
    q = select(Course)

    if user.role == "student":
        # Для студента — только опубликованные, в его направлениях и уровнем ≤ target
        q = q.where(Course.status == "published")
        if user.directions:
            q = q.where(Course.category_id.in_(user.directions))
        else:
            # Профиль не заполнен — пустая выдача
            q = q.where(Course.id == -1)
        allowed = LEVELS_LE.get(user.target_level or "beginner", ["beginner"])
        q = q.where(Course.level.in_(allowed))
    else:
        # teacher / admin — без автофильтра, но уважают переданные параметры
        if status_filter:
            q = q.where(Course.status == status_filter)

    if search:
        q = q.where(Course.title.ilike(f"%{search}%"))
    if level:
        q = q.where(Course.level == level)
    if category_id:
        q = q.where(Course.category_id == category_id)

    return q.order_by(Course.created_at.desc())


def can_access_course(user: User, course: Course) -> bool:
    """Может ли пользователь видеть/открывать конкретный курс."""
    if user.role in ("teacher", "admin"):
        return True
    if course.status != "published":
        return False
    if not user.directions or course.category_id not in user.directions:
        return False
    allowed = LEVELS_LE.get(user.target_level or "beginner", ["beginner"])
    return course.level in allowed


async def assert_can_access(db: AsyncSession, user: User, course: Course) -> None:
    """Бросает 403 COURSE_NOT_IN_PROFILE если курс не в профиле студента."""
    from fastapi import HTTPException, status as http_status

    if can_access_course(user, course):
        return
    raise HTTPException(
        http_status.HTTP_403_FORBIDDEN,
        detail={
            "code": "COURSE_NOT_IN_PROFILE",
            "message": "Этот курс не входит в вашу программу. Измените направления и уровни в настройках профиля",
        },
    )
