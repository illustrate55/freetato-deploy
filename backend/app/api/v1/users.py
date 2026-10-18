"""Users: профиль, статистика, админ-управление."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.permissions import require_role
from app.core.security import hash_password
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.user import (
    RoleChange,
    UserCreateAdmin,
    UserListResponse,
    UserPublic,
    UserStats,
    UserUpdateAdmin,
    UserUpdateMe,
)

router = APIRouter()


@router.get("/me", response_model=UserPublic, summary="Текущий пользователь")
async def get_me(user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.model_validate(user)


@router.patch("/me", response_model=UserPublic, summary="Обновить свой профиль")
async def update_me(
    payload: UserUpdateMe,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return UserPublic.model_validate(user)


@router.get("/me/stats", response_model=UserStats, summary="KPI пользователя")
async def my_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserStats:
    active = (
        await db.execute(
            select(func.count(Enrollment.id)).where(
                Enrollment.user_id == user.id, Enrollment.status == "active"
            )
        )
    ).scalar() or 0
    completed = (
        await db.execute(
            select(func.count(Enrollment.id)).where(
                Enrollment.user_id == user.id, Enrollment.status == "completed"
            )
        )
    ).scalar() or 0
    return UserStats(active_courses=int(active), completed_courses=int(completed))


@router.get("", response_model=UserListResponse, summary="Список пользователей (admin)")
async def list_users(
    role: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    q = select(User)
    if role:
        q = q.where(User.role == role)
    if search:
        like = f"%{search}%"
        q = q.where(or_(User.email.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like)))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar() or 0
    q = q.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(q)).scalars().all()
    return UserListResponse(
        items=[UserPublic.model_validate(u) for u in items],
        total=int(total),
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED, summary="Создать пользователя (admin)")
async def create_user(
    payload: UserCreateAdmin,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    exists = (await db.execute(select(User).where(User.email == payload.email.lower()))).scalar_one_or_none()
    if exists:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_TAKEN", "message": "Email уже занят"},
        )
    new_user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        position=payload.position,
        role=payload.role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return UserPublic.model_validate(new_user)


@router.patch("/{user_id}", response_model=UserPublic, summary="Изменить пользователя (admin)")
async def update_user(
    user_id: int,
    payload: UserUpdateAdmin,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(target, k, v)
    await db.commit()
    await db.refresh(target)
    return UserPublic.model_validate(target)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить пользователя (admin)")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    if user_id == admin.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "CANNOT_DELETE_SELF", "message": "Нельзя удалить самого себя"},
        )
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    await db.delete(target)
    await db.commit()


@router.post("/{user_id}/role", response_model=UserPublic, summary="Сменить роль (admin)")
async def change_user_role(
    user_id: int,
    payload: RoleChange,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> UserPublic:
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Пользователь не найден")
    target.role = payload.role
    await db.commit()
    await db.refresh(target)
    return UserPublic.model_validate(target)
