"""Модули внутри курса."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.permissions import require_role
from app.models.course import Course
from app.models.module import Module
from app.models.user import User
from app.schemas.module import ModuleCreate, ModulePublic, ModuleUpdate

router = APIRouter()


def _ensure_can_edit_course(course: Course, user: User) -> None:
    if user.role == "admin":
        return
    if user.role == "teacher" and course.author_id == user.id:
        return
    raise HTTPException(
        status.HTTP_403_FORBIDDEN,
        detail={"code": "FORBIDDEN", "message": "Можно редактировать только свои курсы"},
    )


@router.post(
    "/courses/{course_id}/modules",
    response_model=ModulePublic,
    status_code=status.HTTP_201_CREATED,
    summary="Создать модуль",
)
async def create_module(
    course_id: int,
    payload: ModuleCreate,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> ModulePublic:
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Курс не найден")
    _ensure_can_edit_course(course, user)

    next_sort = (
        await db.execute(
            select(func.coalesce(func.max(Module.sort_order), 0)).where(Module.course_id == course_id)
        )
    ).scalar() or 0
    module = Module(
        course_id=course_id,
        title=payload.title,
        description=payload.description,
        sort_order=payload.sort_order or int(next_sort) + 1,
    )
    db.add(module)
    await db.commit()
    await db.refresh(module)
    return ModulePublic(
        id=module.id,
        course_id=module.course_id,
        title=module.title,
        description=module.description,
        sort_order=module.sort_order,
        lessons=[],
        created_at=module.created_at,
    )


@router.patch("/modules/{module_id}", response_model=ModulePublic, summary="Обновить модуль")
async def update_module(
    module_id: int,
    payload: ModuleUpdate,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> ModulePublic:
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Модуль не найден")
    course = await db.get(Course, module.course_id)
    _ensure_can_edit_course(course, user)
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(module, k, v)
    await db.commit()
    await db.refresh(module)
    return ModulePublic(
        id=module.id,
        course_id=module.course_id,
        title=module.title,
        description=module.description,
        sort_order=module.sort_order,
        lessons=[],
        created_at=module.created_at,
    )


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить модуль")
async def delete_module(
    module_id: int,
    user: User = Depends(require_role("teacher")),
    db: AsyncSession = Depends(get_db),
) -> None:
    module = await db.get(Module, module_id)
    if not module:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Модуль не найден")
    course = await db.get(Course, module.course_id)
    _ensure_can_edit_course(course, user)
    await db.delete(module)
    await db.commit()
