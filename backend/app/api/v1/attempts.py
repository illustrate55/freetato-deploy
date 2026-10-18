"""Submit и просмотр результата попытки теста."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.attempt import AttemptAnswer, QuizAttempt
from app.models.lesson import Lesson
from app.models.quiz import QuizQuestion
from app.models.user import User
from app.schemas.quiz import AnswerResult, AttemptResult, AttemptSubmit
from app.services.progress_service import (
    mark_lesson_completed,
    recalc_enrollment_progress,
)
from app.services.quiz_service import grade_attempt

router = APIRouter()


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptResult, summary="Сдать попытку (синхронная проверка)")
async def submit_attempt(
    attempt_id: int,
    payload: AttemptSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttemptResult:
    attempt = await db.get(QuizAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Попытка не найдена")
    if attempt.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Чужая попытка")
    if attempt.status == "submitted":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "ALREADY_SUBMITTED", "message": "Попытка уже сдана"},
        )

    result = await grade_attempt(db, attempt, payload)

    # Если passed — отмечаем урок quiz завершённым и пересчитываем прогресс
    if result.passed:
        lesson = (
            await db.execute(select(Lesson).where(Lesson.quiz_id == attempt.quiz_id))
        ).scalar_one_or_none()
        if lesson:
            await mark_lesson_completed(db, user.id, lesson.id, attempt.enrollment_id)
            await recalc_enrollment_progress(db, attempt.enrollment_id)

    return result


@router.get("/attempts/{attempt_id}/result", response_model=AttemptResult, summary="Полный разбор попытки")
async def attempt_result(
    attempt_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AttemptResult:
    attempt = await db.get(QuizAttempt, attempt_id)
    if not attempt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Попытка не найдена")
    if attempt.user_id != user.id and user.role not in ("teacher", "admin"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Чужая попытка")

    answers = (
        await db.execute(select(AttemptAnswer).where(AttemptAnswer.attempt_id == attempt_id))
    ).scalars().all()

    res_answers: list[AnswerResult] = []
    for a in answers:
        question = await db.get(QuizQuestion, a.question_id)
        correct_ids = []
        explanation = None
        correct_text = None
        if question:
            from app.models.quiz import QuizAnswer

            ca = (
                await db.execute(
                    select(QuizAnswer.id).where(
                        QuizAnswer.question_id == question.id, QuizAnswer.is_correct.is_(True)
                    )
                )
            ).scalars().all()
            correct_ids = [int(x) for x in ca]
            explanation = question.explanation
            correct_text = question.correct_text
        res_answers.append(
            AnswerResult(
                question_id=a.question_id,
                is_correct=a.is_correct,
                points_awarded=a.points_awarded,
                explanation=explanation,
                correct_answer_ids=correct_ids,
                correct_text=correct_text,
            )
        )
    return AttemptResult(
        attempt_id=attempt.id,
        quiz_id=attempt.quiz_id,
        score=attempt.score,
        max_score=attempt.max_score,
        score_percent=attempt.score_percent,
        passed=attempt.passed,
        submitted_at=attempt.submitted_at or attempt.started_at,
        answers=res_answers,
    )
