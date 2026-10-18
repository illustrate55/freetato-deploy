"""Адаптер GigaChat: единый интерфейс chat() с моделями pro/max."""
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class AIResponse:
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model: str = ""


MODEL_MAP = {"pro": "GigaChat-2-Pro", "max": "GigaChat-2-Max", "lite": "GigaChat-2"}


class AIProviderNotConfigured(Exception):
    """GIGACHAT_CREDENTIALS не задан — ИИ-функции недоступны."""


class GigaChatProvider:
    """Обёртка вокруг SDK gigachat. Лениво создаёт клиент при первом запросе."""

    def __init__(self) -> None:
        self.credentials = settings.GIGACHAT_CREDENTIALS
        self.scope = settings.GIGACHAT_SCOPE
        self.ca_bundle = settings.GIGACHAT_CA_BUNDLE_FILE
        self.verify_ssl = settings.GIGACHAT_VERIFY_SSL_CERTS

    def is_configured(self) -> bool:
        return bool(self.credentials)

    async def chat(
        self,
        messages: list[dict],
        model: str = "pro",
        temperature: float = 0.4,
        max_tokens: int = 4096,
    ) -> AIResponse:
        if not self.is_configured():
            raise AIProviderNotConfigured(
                "ИИ-провайдер не настроен. Заполните GIGACHAT_CREDENTIALS в .env "
                "и перезапустите контейнер."
            )

        # Импорт здесь, чтобы при отсутствии gigachat-пакета приложение всё равно поднялось
        from gigachat import GigaChat
        from gigachat.models import Chat, Messages, MessagesRole

        gc_model = MODEL_MAP.get(model, MODEL_MAP["pro"])
        gc_messages = [
            Messages(role=MessagesRole(m["role"]), content=m["content"]) for m in messages
        ]

        kwargs: dict = {
            "credentials": self.credentials,
            "scope": self.scope,
            "verify_ssl_certs": self.verify_ssl,
        }
        if self.verify_ssl and self.ca_bundle:
            # Подключаем сертификат только если verify включён и файл указан
            import os

            if os.path.isfile(self.ca_bundle):
                kwargs["ca_bundle_file"] = self.ca_bundle

        async with GigaChat(**kwargs) as client:
            payload = Chat(
                messages=gc_messages,
                model=gc_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            resp = await client.achat(payload)

        usage = getattr(resp, "usage", None)
        return AIResponse(
            content=resp.choices[0].message.content,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage, "total_tokens", 0) or 0,
            model=gc_model,
        )


_provider: GigaChatProvider | None = None


def get_provider() -> GigaChatProvider:
    global _provider
    if _provider is None:
        _provider = GigaChatProvider()
    return _provider
