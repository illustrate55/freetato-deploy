"""Генерация уникальных slug-ов для курсов."""
import secrets

from slugify import slugify as _slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def slugify(text: str) -> str:
    return _slugify(text, max_length=120) or "course"


async def make_unique_slug(db: AsyncSession, model, base: str, exclude_id: int | None = None) -> str:
    """Возвращает slug, гарантированно уникальный в столбце model.slug.

    Если базовый slug занят, добавляет суффикс -2, -3, ... При желании можно
    исключить текущую запись из проверки (для PATCH с переименованием).
    """
    base_slug = slugify(base)
    candidate = base_slug
    n = 2
    while True:
        q = select(model).where(model.slug == candidate)
        if exclude_id is not None:
            q = q.where(model.id != exclude_id)
        existing = (await db.execute(q)).scalar_one_or_none()
        if existing is None:
            return candidate
        candidate = f"{base_slug}-{n}"
        n += 1
        # Защита от бесконечного цикла на крайний случай
        if n > 1000:
            return f"{base_slug}-{secrets.token_hex(4)}"
