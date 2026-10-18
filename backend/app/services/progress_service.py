"""Расчёт прогресса студента по курсу."""
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.module import Module


async def get_or_create_progress(
    db: AsyncSession, user_id: int, lesson_id: int, enrollment_id: int
) -> LessonProgress:
    existing = await db.execute(
        select(LessonProgress).where(
            LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id
        )
    )
    row = existing.scalar_one_or_none()
    if row:
        return row
    row = LessonProgress(
        user_id=user_id,
        lesson_id=lesson_id,
        enrollment_id=enrollment_id,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    return row


async def mark_lesson_completed(
    db: AsyncSession, user_id: int, lesson_id: int, enrollment_id: int
) -> None:
    progress = await get_or_create_progress(db, user_id, lesson_id, enrollment_id)
    progress.status = "completed"
    progress.completed_at = datetime.now(timezone.utc)
    progress.last_seen_at = datetime.now(timezone.utc)
    await db.flush()


async def recalc_enrollment_progress(db: AsyncSession, enrollment_id: int) -> Enrollment | None:
    """Пересчитывает progress_percent. Вызывается после изменения lesson_progress."""
    enr = await db.get(Enrollment, enrollment_id)
    if not enr:
        return None

    total_q = (
        select(func.count(Lesson.id))
        .join(Module, Lesson.module_id == Module.id)
        .where(Module.course_id == enr.course_id, Lesson.is_required.is_(True))
    )
    total = (await db.execute(total_q)).scalar() or 0

    if total == 0:
        enr.progress_percent = 0
        await db.commit()
        return enr

    completed_q = (
        select(func.count(LessonProgress.id))
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .where(
            LessonProgress.enrollment_id == enrollment_id,
            LessonProgress.status == "completed",
            Lesson.is_required.is_(True),
        )
    )
    completed = (await db.execute(completed_q)).scalar() or 0
    enr.progress_percent = round(completed * 100 / total)

    if enr.progress_percent >= 100 and enr.status != "completed":
        enr.status = "completed"
        enr.completed_at = datetime.now(timezone.utc)

    await db.commit()
    return enr


async def recalc_all_for_course(db: AsyncSession, course_id: int) -> None:
    """Пересчёт всех записей курса (например, после удаления урока)."""
    enrollments = (
        await db.execute(select(Enrollment.id).where(Enrollment.course_id == course_id))
    ).scalars().all()
    for enr_id in enrollments:
        await recalc_enrollment_progress(db, enr_id)


async def get_lessons_status_map(db: AsyncSession, enrollment_id: int) -> dict[str, str]:
    rows = (
        await db.execute(
            select(LessonProgress.lesson_id, LessonProgress.status).where(
                LessonProgress.enrollment_id == enrollment_id
            )
        )
    ).all()
    return {str(r[0]): r[1] for r in rows}
