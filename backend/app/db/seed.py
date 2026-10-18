"""Сидинг при первом запуске.

Создаёт:
- 7 категорий-направлений (Backend Go, Backend Python, Frontend, БД,
  Инфраструктура, DevOps, Алгоритмы)
- admin, teacher, demo-студента (с заполненным профилем для проверки фильтрации)

Курсов / модулей / уроков НЕ создаёт. Если admin уже есть — выходит.
"""
import asyncio
import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.category import Category
from app.models.user import User

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

CATEGORIES = [
    {"name": "Backend на Go",     "slug": "backend-go",     "icon_name": "Server",    "sort_order": 1},
    {"name": "Backend на Python", "slug": "backend-python", "icon_name": "Server",    "sort_order": 2},
    {"name": "Frontend",          "slug": "frontend",       "icon_name": "Layout",    "sort_order": 3},
    {"name": "Базы данных",       "slug": "databases",      "icon_name": "Database",  "sort_order": 4},
    {"name": "Инфраструктура",    "slug": "infrastructure", "icon_name": "Cloud",     "sort_order": 5},
    {"name": "DevOps",            "slug": "devops",         "icon_name": "GitBranch", "sort_order": 6},
    {"name": "Алгоритмы",         "slug": "algorithms",     "icon_name": "Code",      "sort_order": 7},
]


async def seed() -> None:
    async with SessionLocal() as db:
        existing = await db.execute(select(User).where(User.email == settings.DEFAULT_ADMIN_EMAIL))
        if existing.scalar_one_or_none():
            logger.info("Seed skipped: admin уже существует")
            return

        cats: dict[str, Category] = {}
        for c in CATEGORIES:
            cat = Category(**c)
            db.add(cat)
            cats[c["slug"]] = cat
        await db.flush()

        admin = User(
            email=settings.DEFAULT_ADMIN_EMAIL,
            password_hash=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
            first_name="Админ",
            last_name="Платформы",
            role="admin",
        )
        teacher = User(
            email=settings.DEFAULT_TEACHER_EMAIL,
            password_hash=hash_password(settings.DEFAULT_TEACHER_PASSWORD),
            first_name="Демо",
            last_name="Преподаватель",
            role="teacher",
        )
        # demo-студент сделан "универсальным" для удобства тестирования:
        # все 7 направлений, beginner→senior — видит все курсы любого уровня
        student = User(
            email=settings.DEFAULT_DEMO_EMAIL,
            password_hash=hash_password(settings.DEFAULT_DEMO_PASSWORD),
            first_name="Демо",
            last_name="Студент",
            role="student",
            directions=[c.id for c in cats.values()],
            current_level="beginner",
            target_level="senior",
        )
        db.add_all([admin, teacher, student])
        await db.commit()
        logger.info("Seed done: 3 users + 7 categories. 0 courses.")


if __name__ == "__main__":
    asyncio.run(seed())
