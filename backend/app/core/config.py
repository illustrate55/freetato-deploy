"""Конфигурация приложения. Читает .env через pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost"

    # Database
    DATABASE_URL: str
    POSTGRES_USER: str = "freetato"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "freetato"

    # Auth
    JWT_SECRET: str
    JWT_ACCESS_TTL_SECONDS: int = 900
    JWT_REFRESH_TTL_SECONDS: int = 604800

    # Seed
    DEFAULT_ADMIN_EMAIL: str = "admin@freetato.ru"
    DEFAULT_ADMIN_PASSWORD: str = "change_me_admin"
    DEFAULT_TEACHER_EMAIL: str = "teacher@freetato.ru"
    DEFAULT_TEACHER_PASSWORD: str = "change_me_teacher"
    DEFAULT_DEMO_EMAIL: str = "demo@freetato.ru"
    DEFAULT_DEMO_PASSWORD: str = "change_me_demo"

    # AI
    GIGACHAT_CREDENTIALS: str = ""
    GIGACHAT_SCOPE: str = "GIGACHAT_API_PERS"
    GIGACHAT_CA_BUNDLE_FILE: str = ""
    GIGACHAT_VERIFY_SSL_CERTS: bool = False
    AI_RATE_PACKAGE_PER_DAY: int = 10

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
