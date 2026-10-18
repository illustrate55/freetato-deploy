"""Схемы ИИ-функций: пакетная генерация урока."""
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.task import CheckCriterion


TaskType = Literal["code", "theory", "mixed"]
Level = Literal["beginner", "junior", "middle", "senior"]
QuestionType = Literal["single", "multiple", "text_short"]


class GeneratePackageRequest(BaseModel):
    module_id: int
    topic: str = Field(min_length=3, max_length=200)
    level: Level | None = None
    duration_minutes: int = Field(default=10, ge=3, le=60)
    task_type: TaskType = "code"
    language: str | None = Field(default="python", max_length=50)


# ===== Схема ответа от ИИ (валидация LLM-вывода) =====
class _LessonText(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(ge=1, le=120)
    content_markdown: str = Field(min_length=20)


class _GeneratedAnswer(BaseModel):
    text: str = Field(min_length=1)
    is_correct: bool = False


class _GeneratedQuestion(BaseModel):
    text: str = Field(min_length=1)
    type: QuestionType
    points: int = 1
    explanation: str | None = None
    correct_text: str | None = None
    answers: list[_GeneratedAnswer] = Field(default_factory=list)


class _GeneratedQuiz(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    passing_score: int = Field(default=70, ge=0, le=100)
    questions: list[_GeneratedQuestion] = Field(min_length=1)


class _GeneratedTask(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description_md: str = Field(min_length=20)
    task_type: TaskType = "code"
    language: str | None = None
    requirements: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    reference_solution: str | None = None
    check_criteria: list[CheckCriterion] = Field(min_length=1)
    passing_score: int = Field(default=70, ge=0, le=100)

    @model_validator(mode="after")
    def check_weights_sum(self):
        total = sum(c.weight for c in self.check_criteria)
        if not (0.99 <= total <= 1.01):
            raise ValueError("Сумма весов критериев должна быть равна 1.0")
        return self


class LessonPackageSchema(BaseModel):
    """Структура ответа GigaChat для пакетной генерации."""
    lesson: _LessonText
    quiz: _GeneratedQuiz
    task: _GeneratedTask


# ===== Ответ API =====
class GeneratePackageResponse(BaseModel):
    text_lesson_id: int
    quiz_lesson_id: int
    task_lesson_id: int
    quiz_id: int
    task_id: int
    tokens_used: int
    package: LessonPackageSchema
