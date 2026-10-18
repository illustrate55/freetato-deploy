"""Auth: register, login, refresh, logout, change-password."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.security import JWTError, decode_token
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    TokenPair,
)
from app.schemas.user import ChangePassword, UserPublic
from app.services import auth_service

router = APIRouter()


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация студента (двухшаговая, отправляется одним запросом)",
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await auth_service.register_user(db, payload)
    access, refresh = await auth_service.issue_token_pair(db, user)
    return TokenPair(access_token=access, refresh_token=refresh, user=UserPublic.model_validate(user))


@router.post("/login", response_model=TokenPair, summary="Вход по email и паролю")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await auth_service.authenticate(db, payload.email, payload.password)
    access, refresh = await auth_service.issue_token_pair(db, user)
    return TokenPair(access_token=access, refresh_token=refresh, user=UserPublic.model_validate(user))


@router.post("/refresh", response_model=RefreshResponse, summary="Refresh-rotation: новая пара токенов")
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> RefreshResponse:
    try:
        decoded = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_REFRESH", "message": "Невалидный или истёкший refresh-токен"},
        )
    if decoded.get("type") != "refresh":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_REFRESH", "message": "Ожидается refresh-токен"},
        )
    user_id = int(decoded["sub"])
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "USER_NOT_FOUND", "message": "Пользователь не найден"},
        )
    access, new_refresh = await auth_service.rotate_refresh(db, user, payload.refresh_token)
    return RefreshResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Выход (затирает refresh)")
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.logout(db, user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT, summary="Смена пароля")
async def change_password(
    payload: ChangePassword,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.change_password(db, user, payload.current_password, payload.new_password)
