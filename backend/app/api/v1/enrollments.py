"""Записи на курсы и прогресс."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.user import User
from app.schemas.enrollment import (
    EnrollmentCreate,
    EnrollmentListResponse,
    EnrollmentProgress,
    EnrollmentPublic,
)
from app.services.course_service import can_access_course
from app.services.progress_service import get_lessons_status_map

router = APIRouter()


async def _build_enrollment_public(db: AsyncSession, enr: Enrollment) -> EnrollmentPublic:
    course = await db.get(Course, enr.course_id)
    total = (
        await db.execute(
            select(func.count(Lesson.id))
            .join(Module, Lesson.module_id == Module.id)
            .where(Module.course_id == enr.course_id, Lesson.is_required.is_(True))
        )
    ).scalar() or 0
    completed_count = round(total * enr.progress_percent / 100) if total else 0
    return EnrollmentPublic(
        id=enr.id,
        user_id=enr.user_id,
        course_id=enr.course_id,
        course_title=course.title if course else None,
        course_category_id=course.category_id if course else None,
        status=enr.status,
        progress_percent=enr.progress_percent,
        enrolled_at=enr.enrolled_at,
        completed_at=enr.completed_at,
        last_lesson_id=enr.last_lesson_id,
        lessons_total=int(total),
        lessons_completed=completed_count,
    )


@router.get("/enrollments", response_model=EnrollmentListResponse, summary="Мои записи на курсы")
async def list_enrollments(
    enrollment_status: str | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EnrollmentListResponse:
    q = select(Enrollment).where(Enrollment.user_id == user.id)
    if enrollment_status and enrollment_status != "all":
        q = q.where(Enrollment.status == enrollment_status)
    rows = (await db.execute(q.order_by(Enrollment.enrolled_at.desc()))).scalars().all()
    items = [await _build_enrollment_public(db, e) for e in rows]
    return EnrollmentListResponse(items=items, total=len(items))


@router.post(
    "/enrollments",
    response_model=EnrollmentPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Записаться на курс",
)
async def create_enrollment(
    payload: EnrollmentCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EnrollmentPublic:
    course = await db.get(Course, payload.course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Курс не найден")

    # Студент — только курсы из своего профиля
    if user.role == "student" and not can_access_course(user, course):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "code": "COURSE_NOT_IN_PROFILE",
                "message": "Этот курс не входит в вашу программу. Измените направления и уровни",
            },
        )

    existing = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id, Enrollment.course_id == course.id
            )
        )
    ).scalar_one_or_none()
    if existing:
        return await _build_enrollment_public(db, existing)

    enr = Enrollment(user_id=user.id, course_id=course.id, status="active")
    db.add(enr)
    course.enrollment_count = (course.enrollment_count or 0) + 1
    await db.commit()
    await db.refresh(enr)
    return await _build_enrollment_public(db, enr)


@router.delete("/enrollments/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Отписаться")
async def delete_enrollment(
    enrollment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    enr = await db.get(Enrollment, enrollment_id)
    if not enr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Запись не найдена")
    if enr.user_id != user.id and user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нельзя удалить чужую запись")
    await db.delete(enr)
    await db.commit()


@router.get(
    "/enrollments/{enrollment_id}/progress",
    response_model=EnrollmentProgress,
    summary="Детальный прогресс по урокам",
)
async def enrollment_progress(
    enrollment_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EnrollmentProgress:
    enr = await db.get(Enrollment, enrollment_id)
    if not enr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Запись не найдена")
    if enr.user_id != user.id and user.role not in ("teacher", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Чужой прогресс недоступен")

    course = await db.get(Course, enr.course_id)
    total = (
        await db.execute(
            select(func.count(Lesson.id))
            .join(Module, Lesson.module_id == Module.id)
            .where(Module.course_id == enr.course_id, Lesson.is_required.is_(True))
        )
    ).scalar() or 0
    completed = round(total * enr.progress_percent / 100) if total else 0
    lessons_map = await get_lessons_status_map(db, enr.id)
    return EnrollmentProgress(
        enrollment_id=enr.id,
        course_id=enr.course_id,
        course_title=course.title if course else "",
        progress_percent=enr.progress_percent,
        lessons_total=int(total),
        lessons_completed=completed,
        status=enr.status,
        last_lesson_id=enr.last_lesson_id,
        lessons_status=lessons_map,
    )
