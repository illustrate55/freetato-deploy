"""Тесты: чтение и старт попытки."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_role
from app.models.attempt import QuizAttempt
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.module import Module
from app.models.quiz import Quiz, QuizAnswer, QuizQuestion
from app.models.user import User
from app.schemas.quiz import (
    QuizAnswerPublic,
    QuizAnswerWithCorrect,
    QuizAttemptStart,
    QuizFull,
    QuizFullUpdate,
    QuizPublic,
    QuizQuestionCreate,
    QuizQuestionPublic,
    QuizQuestionWithCorrect,
)

router = APIRouter()


async def _find_enrollment_for_quiz(db: AsyncSession, user: User, quiz_id: int) -> Enrollment | None:
    lesson = (
        await db.execute(select(Lesson).where(Lesson.quiz_id == quiz_id))
    ).scalar_one_or_none()
    if not lesson:
        return None
    module = await db.get(Module, lesson.module_id)
    enr = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.user_id == user.id, Enrollment.course_id == module.course_id
            )
        )
    ).scalar_one_or_none()
    return enr


@router.get(
    "/quizzes/{quiz_id}",
    response_model=QuizPublic,
    summary="Тест (без правильных ответов для студента)",
)
async def get_quiz(
    quiz_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizPublic:
    quiz = await db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Тест не найден")
    questions = (
        await db.execute(
            select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.sort_order)
        )
    ).scalars().all()

    qpub: list[QuizQuestionPublic] = []
    for q in questions:
        answers = (
            await db.execute(
                select(QuizAnswer).where(QuizAnswer.question_id == q.id).order_by(QuizAnswer.sort_order)
            )
        ).scalars().all()
        qpub.append(
            QuizQuestionPublic(
                id=q.id,
                text=q.text,
                type=q.type,
                points=q.points,
                sort_order=q.sort_order,
                answers=[QuizAnswerPublic.model_validate(a) for a in answers],
            )
        )
    return QuizPublic(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        passing_score=quiz.passing_score,
        max_attempts=quiz.max_attempts,
        shuffle_questions=quiz.shuffle_questions,
        show_correct_after=quiz.show_correct_after,
        questions=qpub,
    )


@router.post(
    "/quizzes/{quiz_id}/attempts",
    response_model=QuizAttemptStart,
    status_code=status.HTTP_201_CREATED,
    summary="Начать попытку",
)
async def start_attempt(
    quiz_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuizAttemptStart:
    quiz = await db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Тест не найден")
    enr = await _find_enrollment_for_quiz(db, user, quiz_id)
    if not enr:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={"code": "NOT_ENROLLED", "message": "Сначала запишитесь на курс"},
        )

    attempt = QuizAttempt(
        user_id=user.id,
        quiz_id=quiz_id,
        enrollment_id=enr.id,
        status="in_progress",
        started_at=datetime.now(timezone.utc),
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return QuizAttemptStart(attempt_id=attempt.id, quiz_id=quiz_id, started_at=attempt.started_at)


@router.get(
    "/quizzes/{quiz_id}/full",
    response_model=QuizFull,
    summary="Полная структура теста с правильными ответами (teacher/admin)",
)
async def get_quiz_full(
    quiz_id: int,
    _user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> QuizFull:
    quiz = await db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Тест не найден")
    questions = (
        await db.execute(
            select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id).order_by(QuizQuestion.sort_order)
        )
    ).scalars().all()

    qfull: list[QuizQuestionWithCorrect] = []
    for q in questions:
        answers = (
            await db.execute(
                select(QuizAnswer).where(QuizAnswer.question_id == q.id).order_by(QuizAnswer.sort_order)
            )
        ).scalars().all()
        qfull.append(
            QuizQuestionWithCorrect(
                id=q.id,
                text=q.text,
                type=q.type,
                points=q.points,
                sort_order=q.sort_order,
                explanation=q.explanation,
                correct_text=q.correct_text,
                answers=[QuizAnswerWithCorrect.model_validate(a) for a in answers],
            )
        )
    return QuizFull(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        passing_score=quiz.passing_score,
        max_attempts=quiz.max_attempts,
        shuffle_questions=quiz.shuffle_questions,
        show_correct_after=quiz.show_correct_after,
        questions=qfull,
    )


@router.put(
    "/quizzes/{quiz_id}/full",
    response_model=QuizFull,
    summary="Полная замена структуры теста (teacher/admin)",
)
async def update_quiz_full(
    quiz_id: int,
    payload: QuizFullUpdate,
    _user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> QuizFull:
    quiz = await db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Тест не найден")

    quiz.title = payload.title
    quiz.description = payload.description
    quiz.passing_score = payload.passing_score
    quiz.max_attempts = payload.max_attempts
    quiz.shuffle_questions = payload.shuffle_questions
    quiz.show_correct_after = payload.show_correct_after

    # Удаляем все старые вопросы (cascade удалит ответы)
    old_questions = (
        await db.execute(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz_id))
    ).scalars().all()
    for q in old_questions:
        await db.delete(q)
    await db.flush()

    # Создаём заново
    for idx, q in enumerate(payload.questions):
        question = QuizQuestion(
            quiz_id=quiz_id,
            text=q.text,
            type=q.type,
            points=q.points,
            explanation=q.explanation,
            correct_text=(q.correct_text.strip() if q.correct_text else None),
            sort_order=idx,
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
    await db.commit()

    return await get_quiz_full(quiz_id=quiz_id, _user=_user, db=db)


@router.post(
    "/quizzes/{quiz_id}/questions",
    response_model=QuizQuestionPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Добавить вопрос (teacher/admin)",
)
async def add_question(
    quiz_id: int,
    payload: QuizQuestionCreate,
    _user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> QuizQuestionPublic:
    quiz = await db.get(Quiz, quiz_id)
    if not quiz:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Тест не найден")

    last_sort = (
        await db.execute(
            select(QuizQuestion.sort_order)
            .where(QuizQuestion.quiz_id == quiz_id)
            .order_by(QuizQuestion.sort_order.desc())
        )
    ).scalar() or 0
    question = QuizQuestion(
        quiz_id=quiz_id,
        text=payload.text,
        type=payload.type,
        points=payload.points,
        explanation=payload.explanation,
        correct_text=(payload.correct_text.strip() if payload.correct_text else None),
        sort_order=int(last_sort) + 1,
    )
    db.add(question)
    await db.flush()

    answers_pub: list[QuizAnswerPublic] = []
    for idx, a in enumerate(payload.answers):
        ans = QuizAnswer(question_id=question.id, text=a.text, is_correct=a.is_correct, sort_order=idx)
        db.add(ans)
        await db.flush()
        answers_pub.append(QuizAnswerPublic.model_validate(ans))
    await db.commit()

    return QuizQuestionPublic(
        id=question.id,
        text=question.text,
        type=question.type,
        points=question.points,
        sort_order=question.sort_order,
        answers=answers_pub,
    )
