"""Мгновенная проверка тестов: single / multiple / text_short."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attempt import AttemptAnswer, QuizAttempt
from app.models.quiz import Quiz, QuizQuestion
from app.schemas.quiz import AnswerResult, AttemptResult, AttemptSubmit


async def get_quiz_with_questions(db: AsyncSession, quiz_id: int) -> Quiz | None:
    q = (
        select(Quiz)
        .where(Quiz.id == quiz_id)
        .options(selectinload(Quiz.questions).selectinload(QuizQuestion.answers))
    )
    return (await db.execute(q)).scalar_one_or_none()


async def grade_attempt(
    db: AsyncSession, attempt: QuizAttempt, payload: AttemptSubmit
) -> AttemptResult:
    """Сравнивает ответы студента с эталонами. Полностью синхронная проверка."""
    quiz = await get_quiz_with_questions(db, attempt.quiz_id)
    if quiz is None:
        raise ValueError("Тест не найден")

    questions_by_id = {q.id: q for q in quiz.questions}
    answers_by_qid = {a.question_id: a for a in payload.answers}

    total_score = 0
    max_score = 0
    results: list[AnswerResult] = []

    for question in quiz.questions:
        max_score += question.points
        student = answers_by_qid.get(question.id)
        is_correct = False
        points = 0

        if student is not None:
            if question.type == "single":
                correct_ids = sorted([a.id for a in question.answers if a.is_correct])
                given = sorted(student.selected_answer_ids or [])
                is_correct = given == correct_ids
            elif question.type == "multiple":
                correct_set = {a.id for a in question.answers if a.is_correct}
                given_set = set(student.selected_answer_ids or [])
                is_correct = correct_set == given_set and len(correct_set) > 0
            elif question.type == "text_short":
                expected = (question.correct_text or "").strip().lower()
                given = (student.answer_text or "").strip().lower()
                is_correct = bool(expected) and given == expected

        if is_correct:
            points = question.points
            total_score += points

        # Сохраняем ответ студента в БД
        db.add(
            AttemptAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                answer_text=student.answer_text if student else None,
                selected_answer_ids=list(student.selected_answer_ids) if student else [],
                is_correct=is_correct,
                points_awarded=points,
            )
        )

        results.append(
            AnswerResult(
                question_id=question.id,
                is_correct=is_correct,
                points_awarded=points,
                explanation=question.explanation,
                correct_answer_ids=[a.id for a in question.answers if a.is_correct],
                correct_text=question.correct_text,
            )
        )

    score_percent = round(total_score * 100 / max_score) if max_score > 0 else 0
    passed = score_percent >= quiz.passing_score

    attempt.score = total_score
    attempt.max_score = max_score
    attempt.score_percent = score_percent
    attempt.passed = passed
    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc)
    await db.commit()

    return AttemptResult(
        attempt_id=attempt.id,
        quiz_id=attempt.quiz_id,
        score=total_score,
        max_score=max_score,
        score_percent=score_percent,
        passed=passed,
        submitted_at=attempt.submitted_at,
        answers=results,
    )
