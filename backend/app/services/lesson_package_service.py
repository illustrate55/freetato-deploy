"""Создание трёх связанных уроков (text + quiz + task) из ИИ-пакета.

Всё внутри одной транзакции. Лимит 10 пакетов в сутки на teacher.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_usage import AIUsage
from app.models.course import Course
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.quiz import Quiz, QuizAnswer, QuizQuestion
from app.models.task import Task
from app.models.user import User
from app.schemas.ai import GeneratePackageRequest, LessonPackageSchema
from app.services.ai_service import AIProviderNotConfigured, generate_lesson_package

logger = logging.getLogger(__name__)


async def check_rate_limit(db: AsyncSession, user_id: int) -> None:
    since = datetime.now(timezone.utc) - timedelta(days=1)
    used = (
        await db.execute(
            select(func.count(AIUsage.id)).where(
                AIUsage.user_id == user_id,
                AIUsage.scenario == "lesson_package",
                AIUsage.created_at >= since,
            )
        )
    ).scalar() or 0
    if used >= settings.AI_RATE_PACKAGE_PER_DAY:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "AI_RATE_LIMIT",
                "message": "Лимит ИИ-генерации исчерпан. Попробуйте завтра",
            },
        )


async def _next_sort_order(db: AsyncSession, module_id: int) -> int:
    last = (
        await db.execute(
            select(func.coalesce(func.max(Lesson.sort_order), 0)).where(Lesson.module_id == module_id)
        )
    ).scalar() or 0
    return int(last) + 1


async def create_package(
    db: AsyncSession, user: User, payload: GeneratePackageRequest
) -> dict:
    """Делает ИИ-запрос и в одной транзакции создаёт 3 урока + quiz + task."""
    module = await db.get(Module, payload.module_id)
    if not module:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"code": "MODULE_NOT_FOUND", "message": "Модуль не найден"},
        )
    course = await db.get(Course, module.course_id)
    if not course:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail={"code": "COURSE_NOT_FOUND", "message": "Курс не найден"},
        )

    # teacher может работать только со своими курсами
    if user.role == "teacher" and course.author_id != user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Нельзя редактировать чужой курс"},
        )

    await check_rate_limit(db, user.id)

    level = payload.level or course.level
    try:
        package, tokens = await generate_lesson_package(
            course_title=course.title,
            module_title=module.title,
            topic=payload.topic,
            level=level,
            duration_minutes=payload.duration_minutes,
            task_type=payload.task_type,
            language=payload.language or "python",
        )
    except AIProviderNotConfigured as e:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "AI_PROVIDER_NOT_CONFIGURED", "message": str(e)},
        )

    sort_order = await _next_sort_order(db, module.id)
    text_lesson, quiz_lesson, task_lesson, quiz_obj, task_obj = await _persist_package(
        db, module.id, package, sort_order
    )

    db.add(
        AIUsage(
            user_id=user.id,
            scenario="lesson_package",
            tokens_used=tokens,
            model="GigaChat-2-Pro",
        )
    )
    await db.commit()

    return {
        "text_lesson_id": text_lesson.id,
        "quiz_lesson_id": quiz_lesson.id,
        "task_lesson_id": task_lesson.id,
        "quiz_id": quiz_obj.id,
        "task_id": task_obj.id,
        "tokens_used": tokens,
        "package": package.model_dump(),
    }


async def _persist_package(
    db: AsyncSession, module_id: int, package: LessonPackageSchema, base_sort: int
):
    # 1) Текстовый урок
    text_lesson = Lesson(
        module_id=module_id,
        title=package.lesson.title,
        type="text",
        sort_order=base_sort,
        duration_minutes=package.lesson.duration_minutes,
        content_markdown=package.lesson.content_markdown,
    )
    db.add(text_lesson)
    await db.flush()

    # 2) Quiz
    quiz_obj = Quiz(
        title=package.quiz.title,
        passing_score=package.quiz.passing_score,
    )
    db.add(quiz_obj)
    await db.flush()

    for idx, q in enumerate(package.quiz.questions):
        question = QuizQuestion(
            quiz_id=quiz_obj.id,
            text=q.text,
            type=q.type,
            points=q.points,
            explanation=q.explanation,
            sort_order=idx,
            correct_text=(q.correct_text.strip() if q.correct_text else None),
        )
        db.add(question)
        await db.flush()
        for a_idx, a in enumerate(q.answers or []):
            db.add(
                QuizAnswer(
                    question_id=question.id,
                    text=a.text,
                    is_correct=a.is_correct,
                    sort_order=a_idx,
                )
            )

    quiz_lesson = Lesson(
        module_id=module_id,
        title=package.quiz.title,
        type="quiz",
        sort_order=base_sort + 1,
        duration_minutes=10,
        quiz_id=quiz_obj.id,
    )
    db.add(quiz_lesson)
    await db.flush()

    # 3) Task
    task_obj = Task(
        title=package.task.title,
        description_md=package.task.description_md,
        task_type=package.task.task_type,
        language=package.task.language,
        requirements=package.task.requirements,
        hints=package.task.hints,
        check_criteria=[c.model_dump() for c in package.task.check_criteria],
        reference_solution=package.task.reference_solution,
        passing_score=package.task.passing_score,
    )
    db.add(task_obj)
    await db.flush()

    task_lesson = Lesson(
        module_id=module_id,
        title=package.task.title,
        type="task",
        sort_order=base_sort + 2,
        duration_minutes=20,
        task_id=task_obj.id,
    )
    db.add(task_lesson)
    await db.flush()

    return text_lesson, quiz_lesson, task_lesson, quiz_obj, task_obj
