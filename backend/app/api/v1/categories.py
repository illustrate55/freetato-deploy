"""Категории-направления."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_role
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryPublic, CategoryUpdate

router = APIRouter()


@router.get("", response_model=list[CategoryPublic], summary="Список направлений (публичный)")
async def list_categories(
    db: AsyncSession = Depends(get_db),
) -> list[CategoryPublic]:
    rows = (
        await db.execute(select(Category).order_by(Category.sort_order, Category.id))
    ).scalars().all()
    return [CategoryPublic.model_validate(c) for c in rows]


@router.post("", response_model=CategoryPublic, status_code=status.HTTP_201_CREATED, summary="Создать (admin)")
async def create_category(
    payload: CategoryCreate,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> CategoryPublic:
    exists = (
        await db.execute(select(Category).where(Category.slug == payload.slug))
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={"code": "SLUG_TAKEN", "message": "slug уже существует"},
        )
    cat = Category(**payload.model_dump())
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoryPublic.model_validate(cat)


@router.patch("/{category_id}", response_model=CategoryPublic, summary="Обновить (admin)")
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> CategoryPublic:
    cat = await db.get(Category, category_id)
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Категория не найдена")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(cat, k, v)
    await db.commit()
    await db.refresh(cat)
    return CategoryPublic.model_validate(cat)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить (admin)")
async def delete_category(
    category_id: int,
    _admin: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    cat = await db.get(Category, category_id)
    if not cat:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Категория не найдена")
    await db.delete(cat)
    await db.commit()
