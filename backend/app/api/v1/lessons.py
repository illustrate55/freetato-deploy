"""Уроки: ручное создание, чтение содержимого, отметка завершения для текстовых."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_role
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.quiz import Quiz
from app.models.task import Task
from app.models.user import User
from app.schemas.lesson import LessonCreate, LessonPublic, LessonUpdate
from app.services.course_service import assert_can_access
from app.services.progress_service import (
    mark_lesson_completed,
    recalc_enrollment_progress,
)

router = APIRouter()


def _ensure_can_edit(course: Course, user: User) -> None:
    if user.role == "admin":
        return
    if user.role == "teacher" and course.author_id == user.id:
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        detail={"code": "FORBIDDEN", "message": "Можно редактировать только свои курсы"},
    )


@router.post(
    "/modules/{module_id}/lessons",
    response_model=LessonPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Создать урок вручную",
)
async def create_lesson(
    module_id: int,
    payload: LessonCreate,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> LessonPublic:
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Модуль не найден")
    course = await db.get(Course, module.course_id)
    _ensure_can_edit(course, user)

    next_sort = (
        await db.execute(
            select(func.coalesce(func.max(Lesson.sort_order), 0)).where(Lesson.module_id == module_id)
        )
    ).scalar() or 0

    lesson = Lesson(
        module_id=module_id,
        title=payload.title,
        type=payload.type,
        content_markdown=payload.content_markdown,
        duration_minutes=payload.duration_minutes,
        sort_order=payload.sort_order or int(next_sort) + 1,
        is_required=payload.is_required,
    )

    # Для quiz/task создаём пустую обвязку, чтобы преподаватель мог наполнить вручную
    if payload.type == "quiz":
        quiz = Quiz(title=payload.title)
        db.add(quiz)
        await db.flush()
        lesson.quiz_id = quiz.id
    elif payload.type == "task":
        task = Task(title=payload.title, description_md=payload.content_markdown or "Описание задания")
        db.add(task)
        await db.flush()
        lesson.task_id = task.id

    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return LessonPublic.model_validate(lesson)


@router.get("/lessons/{lesson_id}", response_model=LessonPublic, summary="Контент урока")
async def get_lesson(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonPublic:
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Урок не найден")
    module = await db.get(Module, lesson.module_id)
    course = await db.get(Course, module.course_id)
    await assert_can_access(db, user, course)
    return LessonPublic.model_validate(lesson)


@router.patch("/lessons/{lesson_id}", response_model=LessonPublic, summary="Обновить урок")
async def update_lesson(
    lesson_id: int,
    payload: LessonUpdate,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> LessonPublic:
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Урок не найден")
    module = await db.get(Module, lesson.module_id)
    course = await db.get(Course, module.course_id)
    _ensure_can_edit(course, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(lesson, k, v)
    await db.commit()
    await db.refresh(lesson)
    return LessonPublic.model_validate(lesson)


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить урок")
async def delete_lesson(
    lesson_id: int,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> None:
    from app.services.progress_service import recalc_all_for_course

    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Урок не найден")
    module = await db.get(Module, lesson.module_id)
    course = await db.get(Course, module.course_id)
    _ensure_can_edit(course, user)
    course_id = course.id
    await db.delete(lesson)
    await db.commit()
    # Пересчёт прогресса всех записей курса
    await recalc_all_for_course(db, course_id)


@router.post(
    "/lessons/{lesson_id}/complete",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Отметить текстовый урок завершённым",
)
async def complete_lesson(
    lesson_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Урок не найден")
    if lesson.type != "text":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "WRONG_LESSON_TYPE", "message": "Завершить вручную можно только текстовый урок"},
        )

    module = await db.get(Module, lesson.module_id)
    enrollment = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id, Enrollment.course_id == module.course_id
            )
        )
    ).scalar_one_or_none()
    if not enrollment:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "NOT_ENROLLED", "message": "Сначала запишитесь на курс"},
        )

    await mark_lesson_completed(db, user.id, lesson.id, enrollment.id)
    enrollment.last_lesson_id = lesson.id
    await db.commit()
    await recalc_enrollment_progress(db, enrollment.id)
