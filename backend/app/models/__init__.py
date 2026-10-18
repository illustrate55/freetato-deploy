"""Регистрация всех ORM-моделей в metadata.

Импорт нужен для Alembic — он подхватывает таблицы через Base.metadata.
"""
from app.models.ai_usage import AIUsage
from app.models.attempt import AttemptAnswer, QuizAttempt
from app.models.category import Category
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.lesson import Lesson
from app.models.lesson_progress import LessonProgress
from app.models.module import Module
from app.models.quiz import Quiz, QuizAnswer, QuizQuestion
from app.models.submission import Submission
from app.models.task import Task
from app.models.user import User

__all__ = [
    "User",
    "Category",
    "Course",
    "Module",
    "Lesson",
    "Enrollment",
    "LessonProgress",
    "Quiz",
    "QuizQuestion",
    "QuizAnswer",
    "QuizAttempt",
    "AttemptAnswer",
    "Task",
    "Submission",
    "AIUsage",
]
