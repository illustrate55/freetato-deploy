"""Курсы: каталог с автофильтрацией для студента, CRUD для teacher/admin."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_role
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.user import User
from app.schemas.course import (
    CourseCreate,
    CourseListResponse,
    CoursePublic,
    CourseUpdate,
)
from app.schemas.module import LessonInModule, ModulePublic
from app.services.course_service import assert_can_access, build_courses_query
from app.utils.slug import make_unique_slug

router = APIRouter()


def _course_to_public(course: Course, modules_count: int = 0, lessons_count: int = 0) -> CoursePublic:
    return CoursePublic(
        id=course.id,
        title=course.title,
        slug=course.slug,
        short_description=course.short_description,
        description=course.description,
        category_id=course.category_id,
        author_id=course.author_id,
        level=course.level,
        target_role=course.target_role,
        tags=course.tags or [],
        duration_minutes=course.duration_minutes,
        status=course.status,
        enrollment_count=course.enrollment_count,
        rating_avg=float(course.rating_avg) if course.rating_avg is not None else 0,
        passing_score=course.passing_score,
        modules_count=modules_count,
        lessons_count=lessons_count,
        created_at=course.created_at,
        published_at=course.published_at,
    )


async def _attach_counts(db: AsyncSession, course: Course) -> tuple[int, int]:
    modules_count = (
        await db.execute(
            select(func.count(Module.id)).where(Module.course_id == course.id)
        )
    ).scalar() or 0
    lessons_count = (
        await db.execute(
            select(func.count(Lesson.id))
            .join(Module, Lesson.module_id == Module.id)
            .where(Module.course_id == course.id)
        )
    ).scalar() or 0
    return int(modules_count), int(lessons_count)


@router.get("/courses", response_model=CourseListResponse, summary="Каталог курсов")
async def list_courses(
    search: str | None = None,
    level: str | None = None,
    category_id: int | None = None,
    course_status: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CourseListResponse:
    q = build_courses_query(user, search=search, level=level, category_id=category_id, status_filter=course_status)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    items: list[CoursePublic] = []
    for c in rows:
        modules_count, lessons_count = await _attach_counts(db, c)
        items.append(_course_to_public(c, modules_count, lessons_count))
    return CourseListResponse(items=items, total=int(total), page=page, page_size=page_size)


@router.get("/courses/{course_id}", response_model=CoursePublic, summary="Карточка курса")
async def get_course(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CoursePublic:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Курс не найден")
    await assert_can_access(db, user, course)
    modules_count, lessons_count = await _attach_counts(db, course)
    return _course_to_public(course, modules_count, lessons_count)


@router.get(
    "/courses/{course_id}/modules",
    response_model=list[ModulePublic],
    summary="Программа курса (модули и уроки)",
)
async def get_course_modules(
    course_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ModulePublic]:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Курс не найден")
    await assert_can_access(db, user, course)

    rows = (
        await db.execute(
            select(Module)
            .where(Module.course_id == course_id)
            .order_by(Module.sort_order, Module.id)
            .options(selectinload(Module.lessons))
        )
    ).scalars().all()

    result: list[ModulePublic] = []
    for m in rows:
        lessons = [LessonInModule.model_validate(l) for l in sorted(m.lessons, key=lambda x: x.sort_order)]
        result.append(
            ModulePublic(
                id=m.id,
                course_id=m.course_id,
                title=m.title,
                description=m.description,
                sort_order=m.sort_order,
                lessons=lessons,
                created_at=m.created_at,
            )
        )
    return result


@router.post("/courses", response_model=CoursePublic, status_code=status.HTTP_201_CREATED, summary="Создать курс")
async def create_course(
    payload: CourseCreate,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> CoursePublic:
    # Retry на случай race condition: два POST с одинаковым title видят
    # одинаково свободный slug, второй вставляется → UniqueViolation.
    for _ in range(3):
        slug = await make_unique_slug(db, Course, payload.title)
        course = Course(
            title=payload.title,
            slug=slug,
            short_description=payload.short_description,
            description=payload.description,
            category_id=payload.category_id,
            author_id=user.id,
            level=payload.level,
            target_role=payload.target_role,
            tags=payload.tags,
            duration_minutes=payload.duration_minutes,
            passing_score=payload.passing_score,
            status="draft",
        )
        db.add(course)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        await db.refresh(course)
        return _course_to_public(course)
    raise HTTPException(
        status.HTTP_409_CONFLICT,
        detail={"code": "SLUG_CONFLICT", "message": "Не удалось создать уникальный slug, попробуйте другое название"},
    )


def _ensure_can_edit(course: Course, user: User) -> None:
    if user.role == "admin":
        return
    if user.role == "teacher" and course.author_id == user.id:
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        detail={"code": "FORBIDDEN", "message": "Можно редактировать только свои курсы"},
    )


@router.patch("/courses/{course_id}", response_model=CoursePublic, summary="Обновить курс")
async def update_course(
    course_id: int,
    payload: CourseUpdate,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> CoursePublic:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Курс не найден")
    _ensure_can_edit(course, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(course, k, v)
    await db.commit()
    await db.refresh(course)
    modules_count, lessons_count = await _attach_counts(db, course)
    return _course_to_public(course, modules_count, lessons_count)


@router.post("/courses/{course_id}/publish", response_model=CoursePublic, summary="Опубликовать курс")
async def publish_course(
    course_id: int,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> CoursePublic:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Курс не найден")
    _ensure_can_edit(course, user)

    modules_count, lessons_count = await _attach_counts(db, course)
    if modules_count == 0 or lessons_count == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "EMPTY_COURSE",
                "message": "Для публикации нужен минимум 1 модуль и 1 урок",
            },
        )
    course.status = "published"
    course.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(course)
    return _course_to_public(course, modules_count, lessons_count)


@router.post("/courses/{course_id}/archive", response_model=CoursePublic, summary="Архивировать")
async def archive_course(
    course_id: int,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> CoursePublic:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Курс не найден")
    _ensure_can_edit(course, user)
    course.status = "archived"
    await db.commit()
    await db.refresh(course)
    return _course_to_public(course)


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить (admin)")
async def delete_course(
    course_id: int,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Курс не найден")
    await db.delete(course)
    await db.commit()
