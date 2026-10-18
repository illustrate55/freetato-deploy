"""Фоновая ИИ-проверка решения задания."""
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.ai_usage import AIUsage
from app.models.lesson import Lesson
from app.models.submission import Submission
from app.models.task import Task
from app.services.ai_service import AIProviderNotConfigured, check_task_submission
from app.services.progress_service import (
    mark_lesson_completed,
    recalc_enrollment_progress,
)

logger = logging.getLogger(__name__)


async def run_ai_check(submission_id: int) -> None:
    """Фоновая задача: вызывает GigaChat-Max и сохраняет результат в submissions."""
    async with SessionLocal() as db:
        sub = await db.get(Submission, submission_id)
        if not sub:
            logger.error("Submission %s не найден для ИИ-проверки", submission_id)
            return

        sub.status = "checking"
        await db.commit()

        task = await db.get(Task, sub.task_id)
        if not task:
            sub.status = "error"
            sub.error_message = "Задание не найдено"
            await db.commit()
            return

        try:
            result, tokens = await check_task_submission(task, sub.solution)
        except AIProviderNotConfigured as e:
            sub.status = "error"
            sub.error_message = str(e)
            await db.commit()
            return
        except Exception as e:
            logger.exception("Ошибка ИИ-проверки submission=%s", submission_id)
            sub.status = "error"
            sub.error_message = f"Ошибка ИИ-провайдера: {e}"
            await db.commit()
            return

        sub.status = "checked"
        sub.score_percent = int(result.get("score_percent") or 0)
        sub.is_passed = bool(result.get("is_passed"))
        sub.ai_summary = result.get("summary")
        sub.ai_per_criterion = result.get("per_criterion")
        sub.ai_improvement_tips = result.get("improvement_tips")
        sub.checked_at = datetime.now(timezone.utc)

        # Учёт расхода токенов
        db.add(
            AIUsage(
                user_id=sub.user_id,
                scenario="task_check",
                tokens_used=tokens,
                model="GigaChat-2-Max",
            )
        )
        await db.commit()

        # Если задание сдано — отмечаем урок типа task завершённым и пересчитываем прогресс
        if sub.is_passed:
            lesson = (
                await db.execute(select(Lesson).where(Lesson.task_id == sub.task_id))
            ).scalar_one_or_none()
            if lesson:
                await mark_lesson_completed(db, sub.user_id, lesson.id, sub.enrollment_id)
                await recalc_enrollment_progress(db, sub.enrollment_id)
