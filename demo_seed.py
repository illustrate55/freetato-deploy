"""
Демо-скрипт для видео-демонстрации ВКР.

Создаёт: курс → модуль → урок с заданием → публикует → записывает студента → сдаёт решение на ИИ-проверку.
Запуск: python demo_seed.py
"""
import time
import requests

BASE = "http://localhost/api/v1"

TEACHER = {"email": "teacher@freetato.ru", "password": "Teacher2026Pass"}
STUDENT = {"email": "demo@freetato.ru",    "password": "Demo2026Pass"}


def login(creds: dict) -> str:
    r = requests.post(f"{BASE}/auth/login", json=creds)
    r.raise_for_status()
    token = r.json()["access_token"]
    role = r.json()["user"]["role"]
    print(f"  [login] {creds['email']} ({role}) — OK")
    return token


def h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def step(msg: str):
    print(f"\n{'='*55}\n  {msg}\n{'='*55}")


# ── 1. Логин преподавателя ──────────────────────────────────
step("1. Логин преподавателя")
t_token = login(TEACHER)

# ── 2. Категория ────────────────────────────────────────────
step("2. Получаем категорию 'Backend на Python'")
cats = requests.get(f"{BASE}/categories", headers=h(t_token)).json()
cat = next((c for c in cats if "Python" in c["name"]), cats[0])
cat_id = cat["id"]
print(f"  category_id={cat_id}  name={cat['name']}")

# ── 3. Курс ─────────────────────────────────────────────────
step("3. Создаём курс")
course_payload = {
    "title": "Python для бэкенда: FastAPI + PostgreSQL",
    "short_description": "Практический курс по разработке REST API на FastAPI с PostgreSQL",
    "description": "Курс охватывает проектирование и реализацию серверной части веб-приложений: REST API, аутентификация JWT, работа с БД через SQLAlchemy, контейнеризация Docker.",
    "category_id": cat_id,
    "level": "junior",
    "target_role": "backend",
    "tags": ["python", "fastapi", "postgresql", "docker"],
    "duration_minutes": 480,
    "passing_score": 70,
}
r = requests.post(f"{BASE}/courses", json=course_payload, headers=h(t_token))
r.raise_for_status()
course = r.json()
course_id = course["id"]
print(f"  course_id={course_id}  title={course['title']}  status={course['status']}")

# ── 4. Модуль ───────────────────────────────────────────────
step("4. Создаём модуль")
r = requests.post(f"{BASE}/courses/{course_id}/modules", headers=h(t_token), json={
    "title": "Модуль 1: Основы FastAPI и SQLAlchemy",
    "description": "Роутеры, зависимости, ORM-модели, миграции Alembic",
})
r.raise_for_status()
module = r.json()
module_id = module["id"]
print(f"  module_id={module_id}  title={module['title']}")

# ── 5. Урок с практическим заданием ─────────────────────────
step("5. Создаём урок-задание")
r = requests.post(f"{BASE}/modules/{module_id}/lessons", headers=h(t_token), json={
    "title": "Практическое задание: реализовать эндпоинт регистрации",
    "type": "task",
    "duration_minutes": 60,
    "is_required": True,
})
r.raise_for_status()
lesson = r.json()
lesson_id = lesson["id"]
task_id = lesson["task_id"]
print(f"  lesson_id={lesson_id}  task_id={task_id}")

# ── 6. Наполняем задание критериями ─────────────────────────
step("6. Задаём условие и критерии проверки")
r = requests.patch(f"{BASE}/tasks/{task_id}", headers=h(t_token), json={
    "description_md": (
        "## Задание\n\n"
        "Реализуйте эндпоинт `POST /register` на FastAPI.\n\n"
        "**Требования:**\n"
        "- Принимает `email`, `password`, `first_name`, `last_name`\n"
        "- Хеширует пароль через `bcrypt`\n"
        "- Сохраняет пользователя в базу данных\n"
        "- Возвращает JWT access-токен\n"
        "- Возвращает `201 Created` при успехе\n"
        "- Возвращает `409 Conflict` если email уже занят\n\n"
        "**Стек:** FastAPI, SQLAlchemy (async), passlib bcrypt, python-jose"
    ),
    "task_type": "code",
    "language": "python",
    "requirements": [
        "Использовать FastAPI и Pydantic-схемы",
        "Хеширование пароля через bcrypt (passlib)",
        "JWT-токен в ответе",
        "Обработка дублирующегося email (409)",
    ],
    "hints": [
        "Используй CryptContext из passlib.context",
        "Проверь уникальность email до INSERT",
        "Верни TokenPair с access_token и user",
    ],
    "check_criteria": [
        {"criterion": "Корректная структура эндпоинта FastAPI (роутер, схемы Pydantic)", "weight": 0.25},
        {"criterion": "Пароль хешируется через bcrypt, открытый пароль нигде не хранится", "weight": 0.25},
        {"criterion": "Возвращается JWT access-токен при успешной регистрации", "weight": 0.25},
        {"criterion": "Обработка ошибки дубликата email с кодом 409", "weight": 0.25},
    ],
    "reference_solution": (
        "from fastapi import APIRouter, Depends, HTTPException, status\n"
        "from sqlalchemy.ext.asyncio import AsyncSession\n"
        "from app.core.security import hash_password, create_access_token\n"
        "from app.models.user import User\n"
        "from app.schemas.auth import RegisterRequest, TokenPair\n\n"
        "router = APIRouter()\n\n"
        "@router.post('/register', status_code=201)\n"
        "async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):\n"
        "    existing = await db.execute(select(User).where(User.email == payload.email))\n"
        "    if existing.scalar_one_or_none():\n"
        "        raise HTTPException(409, 'Email already registered')\n"
        "    user = User(\n"
        "        email=payload.email,\n"
        "        password_hash=hash_password(payload.password),\n"
        "        first_name=payload.first_name,\n"
        "        last_name=payload.last_name,\n"
        "    )\n"
        "    db.add(user)\n"
        "    await db.commit()\n"
        "    token = create_access_token({'sub': str(user.id)})\n"
        "    return TokenPair(access_token=token, user=user)\n"
    ),
    "passing_score": 70,
})
r.raise_for_status()
print(f"  task обновлён: {len(r.json()['check_criteria'])} критерия")

# ── 7. Публикуем курс ────────────────────────────────────────
step("7. Публикуем курс")
r = requests.post(f"{BASE}/courses/{course_id}/publish", headers=h(t_token))
r.raise_for_status()
print(f"  status={r.json()['status']}")

# ── 8. Логин студента ────────────────────────────────────────
step("8. Логин студента")
s_token = login(STUDENT)

# ── 9. Запись на курс ────────────────────────────────────────
step("9. Студент записывается на курс")
r = requests.post(f"{BASE}/enrollments", headers=h(s_token), json={"course_id": course_id})
r.raise_for_status()
enrollment = r.json()
print(f"  enrollment_id={enrollment['id']}  status={enrollment['status']}")

# ── 10. Смотрим задание ──────────────────────────────────────
step("10. Студент читает условие задания")
r = requests.get(f"{BASE}/tasks/{task_id}", headers=h(s_token))
r.raise_for_status()
task = r.json()
print(f"  task: {task['title']}")
print(f"  requirements: {len(task['requirements'])} шт.")

# ── 11. Сдаём решение ────────────────────────────────────────
step("11. Студент сдаёт решение")
solution = """
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenPair
from app.core.security import create_access_token
from app.db.session import get_db

router = APIRouter()
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register", response_model=TokenPair, status_code=201)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=payload.email,
        password_hash=pwd_ctx.hash(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return TokenPair(access_token=token, user=user)
"""
r = requests.post(f"{BASE}/tasks/{task_id}/submissions", headers=h(s_token), json={"solution": solution.strip()})
r.raise_for_status()
sub = r.json()
sub_id = sub["submission_id"]
print(f"  submission_id={sub_id}  status={sub['status']}")

# ── 12. Поллинг результата ───────────────────────────────────
step("12. Ждём результат ИИ-проверки...")
for attempt in range(18):
    time.sleep(5)
    r = requests.get(f"{BASE}/submissions/{sub_id}", headers=h(s_token))
    r.raise_for_status()
    result = r.json()
    status_val = result["status"]
    print(f"  [{attempt*5:>3}с] status={status_val}", end="")
    if status_val in ("checked", "error"):
        print()
        break
    print(" — ждём...")
else:
    print("\n  (таймаут 90с — GigaChat долго отвечает, проверь позже)")

# ── Итог ─────────────────────────────────────────────────────
print(f"""
{'='*55}
  ДЕМО-ДАННЫЕ ГОТОВЫ — запиши эти ID для Swagger
{'='*55}
  course_id     = {course_id}
  module_id     = {module_id}
  lesson_id     = {lesson_id}
  task_id       = {task_id}
  submission_id = {sub_id}

  Swagger UI:   http://localhost/docs

  Учётные данные:
    teacher:  teacher@freetato.ru / Teacher2026Pass
    student:  demo@freetato.ru    / Demo2026Pass
    admin:    admin@freetato.ru   / Admin2026Pass

  Сценарий видео:
    1. /docs -- показать все 14 модулей
    2. POST /auth/login (teacher) -- скопировать token -- Authorize
    3. GET  /courses/{course_id} -- карточка курса
    4. GET  /courses/{course_id}/modules -- программа курса
    5. POST /auth/login (student) -- Authorize
    6. GET  /tasks/{task_id} -- условие задания
    7. GET  /submissions/{sub_id} -- результат ИИ-проверки
    8. Терминал: docker ps -- 3 healthy контейнера
{'='*55}
""".format(
    course_id=course_id, module_id=module_id,
    lesson_id=lesson_id, task_id=task_id, sub_id=sub_id,
))
