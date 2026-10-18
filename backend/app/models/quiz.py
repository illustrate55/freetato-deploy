"""Тесты: quizzes / quiz_questions / quiz_answers.

Типы вопросов: single (один правильный), multiple (несколько правильных),
text_short (точное сравнение строки case-insensitive).
"""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(nullable=True)
    passing_score: Mapped[int] = mapped_column(Integer, nullable=False, default=70, server_default="70")
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3, server_default="3")
    shuffle_questions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    show_correct_after: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    questions: Mapped[list["QuizQuestion"]] = relationship(
        back_populates="quiz",
        cascade="all, delete-orphan",
        order_by="QuizQuestion.sort_order",
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    explanation: Mapped[str | None] = mapped_column(nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_text: Mapped[str | None] = mapped_column(nullable=True)

    quiz = relationship("Quiz", back_populates="questions")
    answers: Mapped[list["QuizAnswer"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuizAnswer.sort_order",
    )

    __table_args__ = (
        CheckConstraint("type IN ('single','multiple','text_short')", name="quiz_questions_type_check"),
        Index("ix_quiz_questions_quiz", "quiz_id", "sort_order"),
    )


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    question_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    question = relationship("QuizQuestion", back_populates="answers")
