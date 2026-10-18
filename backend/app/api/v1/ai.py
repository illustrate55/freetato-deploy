"""ИИ-эндпоинт: пакетная генерация урока + статус провайдера."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gigachat_provider import get_provider
from app.api.deps import get_current_user, get_db
from app.core.permissions import require_role
from app.models.user import User
from app.schemas.ai import GeneratePackageRequest, GeneratePackageResponse
from app.services.lesson_package_service import create_package

router = APIRouter()


class AIStatus(BaseModel):
    available: bool
    reason: str


@router.get("/status", response_model=AIStatus, summary="Статус ИИ-провайдера")
async def ai_status(_user: User = Depends(get_current_user)) -> AIStatus:
    """Доступен ли GigaChat. Используется фронтом для дизейбла ИИ-кнопок."""
    provider = get_provider()
    if provider.is_configured():
        return AIStatus(available=True, reason="GigaChat настроен")
    return AIStatus(
        available=False,
        reason="ИИ-провайдер не настроен. Заполните GIGACHAT_CREDENTIALS в .env",
    )


@router.post(
    "/lessons/generate-package",
    response_model=GeneratePackageResponse,
    summary="Создать пакет урока (text + quiz + task) через ИИ",
)
async def generate_package(
    payload: GeneratePackageRequest,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> GeneratePackageResponse:
    result = await create_package(db, user, payload)
    return GeneratePackageResponse(**result)
