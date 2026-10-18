# FREETATO ДПО

Корпоративная LMS-платформа дополнительного профессионального образования.
Каталог курсов с фильтрацией под профиль обучения студента, прохождение
уроков трёх типов (текст, тест, практическое задание), пакетная ИИ-генерация
учебных материалов для преподавателей и автопроверка заданий через GigaChat.

Развёрнутая система: **`https://10.10.10.65/`** (внутренний корпоративный
контур, HTTPS с self-signed сертификатом).

> Сборка рассчитана на **LAN/VPN-режим**. Публикация в открытый интернет
> требует доработок — см. `ПРОВЕРЬ ЭТО/PUBLIC_DEPLOYMENT_NOTES.md`.

## Стек

| Слой | Технологии |
|---|---|
| Frontend | HTML5, CSS3, ES6+ modules — без фреймворков |
| Backend  | Python 3.11, FastAPI, SQLAlchemy 2.x async, Alembic, Pydantic 2 |
| БД       | PostgreSQL 15 |
| ИИ       | GigaChat от Сбера (Pro — генерация, Max — проверка) |
| Деплой   | Docker Compose: postgres + app + nginx |

## Структура

```
freetato-academy/
├── docker-compose.yml
├── .env
├── nginx/
│   ├── nginx.conf                  # dev (HTTP only)
│   └── certs/                      # self-signed для prod
├── _deploy/                        # скрипты деплоя
│   ├── deploy.py
│   ├── audit.py
│   ├── watch.py
│   ├── nginx.prod.conf             # HTTPS + HSTS + no-store
│   └── docker-compose.prod.yml
├── ПРОВЕРЬ ЭТО/                    # документация
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── ER_DIAGRAM.md
│   ├── RBAC_MATRIX.md
│   ├── TEST_PLAN.md
│   ├── PUBLIC_DEPLOYMENT_NOTES.md
│   ├── .env.example
│   └── TZ_FREETATO_LMS_v5.docx
├── backend/
│   ├── Dockerfile
│   ├── alembic/
│   ├── app/
│   │   ├── api/v1/                 # эндпоинты
│   │   ├── core/                   # config, security, RBAC
│   │   ├── db/                     # session, seed
│   │   ├── models/                 # SQLAlchemy
│   │   ├── schemas/                # Pydantic
│   │   ├── services/               # бизнес-логика
│   │   └── ai/                     # GigaChat provider + prompts
│   └── tests/
└── frontend/
    ├── pages/                      # HTML страницы
    ├── css/                        # стили (variables / base / components / layout + pages/)
    ├── js/                         # модули (api / components / pages)
    └── assets/img/dino/            # маскот-динозаврик
```

## Быстрый старт (локально)

```bash
git clone <repo> && cd freetato-academy
cp "ПРОВЕРЬ ЭТО/.env.example" .env
# отредактировать .env (как минимум JWT_SECRET и пароли)

docker compose up -d --build
# дождаться: docker compose logs -f app → "Uvicorn running"
# открыть http://localhost/
```

## Деплой на сервер

```bash
python _deploy/deploy.py <root_password>
```

Скрипт делает:
1. SFTP-sync кода в `/root/freetato/freetato-academy/` на 10.10.10.65.
2. Генерирует self-signed cert в `nginx/certs/`, если ещё нет.
3. Патчит `.env` на сервере: подкидывает HTTPS-origin в `CORS_ORIGINS`,
   очищает `GIGACHAT_CA_BUNDLE_FILE`.
4. `docker compose down + build + up` с prod-overlay.
5. Smoke-проверки health и login.html.

После деплоя — `python _deploy/audit.py <admin_pwd>` прогоняет 63
проверки (содержимое файлов, asset-200, auth-rotation для всех ролей).

Подробнее в `ПРОВЕРЬ ЭТО/ARCHITECTURE.md`.

## Учётки по умолчанию

Создаются `db/seed.py` при первом старте, если в БД ещё нет админа.
Email/пароль берутся из `.env` (`DEFAULT_*_EMAIL` / `DEFAULT_*_PASSWORD`).

| Роль | Что может |
|---|---|
| admin   | Управление пользователями, категориями, статистика. В сайдбаре **только** «Админ-панель». |
| teacher | Создаёт и наполняет свои курсы (вручную или через ИИ). |
| student | Каталог, запись на курс, прохождение уроков. demo-студент сделан универсальным: все 7 направлений, beginner→senior. |

## Аутентификация

- Access-токен JWT HS256, 15 мин, `sessionStorage`.
- Refresh-токен JWT HS256, 7 дней, `sessionStorage`. В payload `jti` —
  токен уникален даже при двух выдачах в одну секунду.
- Хеш refresh-токена в БД — `HMAC-SHA256(JWT_SECRET, token)` (bcrypt
  здесь не годится — обрезает на 72 байтах).
- «Запомни меня» — НЕ persist-сессия. Это локальная история логинов
  в `localStorage.remembered_logins` (массив пар `{email, password}`,
  до 20 штук). На форме входа поле email получает dropdown со всеми
  адресами; выбор автоподставляет пароль. Юзер сам жмёт «Войти».

См. `ПРОВЕРЬ ЭТО/ARCHITECTURE.md` для последовательной диаграммы.

## ИИ-функции

Платформа работает **без GigaChat** — недоступны только пакетная
ИИ-генерация уроков и автопроверка заданий (вернут 503). Остальное
полнофункционально.

### Получение GigaChat-ключа

1. https://developers.sber.ru → войти через СберID.
2. **GigaChat API** → **Создать проект** → **Для физических лиц** (Freemium).
3. **Сгенерировать новый Client Secret** → скопировать **Authorization Key**.
4. В `.env`: `GIGACHAT_CREDENTIALS=<скопированный_ключ>`.
5. `docker compose up -d --force-recreate app` (restart не перечитывает env_file).

Бесплатный лимит: 1 000 000 токенов на 12 месяцев.

## Тесты

```bash
docker compose exec app pytest -v
```

`aiosqlite` в `requirements.txt` — smoke-тесты используют SQLite
в памяти. 5 тестов покрывают health, openapi, требование auth,
регистрацию и валидацию.

## Безопасность

LAN/VPN-режим: brute-force-лимитеры, Basic-auth на Swagger, CSP и
прочая защита от анонимных атак намеренно отсутствуют. Минимум, что
**нужно** поменять перед prod-заливкой:

- `JWT_SECRET` — `openssl rand -hex 64`.
- `POSTGRES_PASSWORD` (+ обновить `DATABASE_URL`).
- `DEFAULT_*_PASSWORD` — заменить заглушки на сильные пароли.

Полный список для публичного деплоя: `ПРОВЕРЬ ЭТО/PUBLIC_DEPLOYMENT_NOTES.md`.

## Резервное копирование

```bash
docker exec freetato-postgres pg_dump -U freetato freetato | gzip > backup.sql.gz
```

## API-документация

- Swagger UI: `https://10.10.10.65/docs` (или `http://localhost/docs` локально)
- ReDoc:      `https://10.10.10.65/redoc`
- OpenAPI:    `https://10.10.10.65/openapi.json`

## Лицензия

Корпоративный проект ООО «FREETATO». Все права защищены.
