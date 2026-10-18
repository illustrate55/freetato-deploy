"""Схемы тестов: вопросы, варианты, попытки."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


QuestionType = Literal["single", "multiple", "text_short"]


class QuizAnswerPublic(BaseModel):
    """Вариант ответа БЕЗ is_correct (для студента)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    sort_order: int


class QuizAnswerWithCorrect(QuizAnswerPublic):
    is_correct: bool


class QuizAnswerCreate(BaseModel):
    text: str = Field(min_length=1)
    is_correct: bool = False


class QuizQuestionPublic(BaseModel):
    """Вопрос для студента — без правильных ответов и без correct_text."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    type: QuestionType
    points: int
    sort_order: int
    answers: list[QuizAnswerPublic] = Field(default_factory=list)


class QuizQuestionWithCorrect(BaseModel):
    """Вопрос для преподавателя/админа — с эталонами."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str
    type: QuestionType
    points: int
    sort_order: int
    explanation: str | None = None
    correct_text: str | None = None
    answers: list[QuizAnswerWithCorrect] = Field(default_factory=list)


class QuizQuestionCreate(BaseModel):
    text: str = Field(min_length=1)
    type: QuestionType
    points: int = 1
    explanation: str | None = None
    correct_text: str | None = None
    answers: list[QuizAnswerCreate] = Field(default_factory=list)


class QuizPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    passing_score: int
    max_attempts: int
    shuffle_questions: bool
    show_correct_after: bool
    questions: list[QuizQuestionPublic] = Field(default_factory=list)


class QuizFull(BaseModel):
    """Полная схема для teacher/admin (с правильными ответами)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None = None
    passing_score: int
    max_attempts: int
    shuffle_questions: bool
    show_correct_after: bool
    questions: list[QuizQuestionWithCorrect] = Field(default_factory=list)


class QuizFullUpdate(BaseModel):
    """PUT-замена всех полей quiz целиком, включая список вопросов."""
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    passing_score: int = Field(default=70, ge=0, le=100)
    max_attempts: int = Field(default=3, ge=1, le=20)
    shuffle_questions: bool = False
    show_correct_after: bool = True
    questions: list[QuizQuestionCreate] = Field(default_factory=list)


class QuizAttemptStart(BaseModel):
    attempt_id: int
    quiz_id: int
    started_at: datetime


class StudentAnswerSubmit(BaseModel):
    question_id: int
    selected_answer_ids: list[int] = Field(default_factory=list)
    answer_text: str | None = None


class AttemptSubmit(BaseModel):
    answers: list[StudentAnswerSubmit] = Field(min_length=1)


class AnswerResult(BaseModel):
    question_id: int
    is_correct: bool
    points_awarded: int
    explanation: str | None = None
    correct_answer_ids: list[int] = Field(default_factory=list)
    correct_text: str | None = None


class AttemptResult(BaseModel):
    attempt_id: int
    quiz_id: int
    score: int
    max_score: int
    score_percent: int
    passed: bool
    submitted_at: datetime
    answers: list[AnswerResult] = Field(default_factory=list)
