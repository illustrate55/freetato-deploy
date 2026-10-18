"""Сборка роутера v1 из всех модулей."""
from fastapi import APIRouter

from app.api.v1 import (
    admin,
    ai,
    attempts,
    auth,
    categories,
    courses,
    enrollments,
    lessons,
    modules,
    quizzes,
    submissions,
    tasks,
    users,
)

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_v1_router.include_router(courses.router, prefix="", tags=["courses"])
api_v1_router.include_router(modules.router, prefix="", tags=["modules"])
api_v1_router.include_router(lessons.router, prefix="", tags=["lessons"])
api_v1_router.include_router(enrollments.router, prefix="", tags=["enrollments"])
api_v1_router.include_router(quizzes.router, prefix="", tags=["quizzes"])
api_v1_router.include_router(attempts.router, prefix="", tags=["attempts"])
api_v1_router.include_router(tasks.router, prefix="", tags=["tasks"])
api_v1_router.include_router(submissions.router, prefix="", tags=["submissions"])
api_v1_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_v1_router.include_router(admin.router, prefix="/admin", tags=["admin"])
