"""Высокоуровневые методы ИИ: пакетная генерация и проверка задания.

Парсинг JSON выполняется с одной повторной попыткой, если LLM вернул невалидный JSON.
"""
import json
import logging
import re
from typing import Any

from app.ai.gigachat_provider import AIProviderNotConfigured, AIResponse, get_provider
from app.ai.prompts import LESSON_PACKAGE_GENERATE, TASK_CHECK
from app.schemas.ai import LessonPackageSchema

logger = logging.getLogger(__name__)


def _strip_json(text: str) -> str:
    text = text.strip()
    # Срезаем тройные кавычки и преамбулу ```json ... ```
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*", "", text).strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text


def _parse_json(content: str) -> Any:
    cleaned = _strip_json(content)
    return json.loads(cleaned)


async def _chat_with_retry(messages: list[dict], model: str, temperature: float, max_tokens: int) -> tuple[Any, AIResponse]:
    """Делает chat-запрос. Если JSON невалидный — повторяет один раз с пониженной temperature.

    Плохой ответ в историю не подкладываем — это удваивает расход токенов.
    """
    provider = get_provider()
    resp = await provider.chat(messages=messages, model=model, temperature=temperature, max_tokens=max_tokens)
    try:
        return _parse_json(resp.content), resp
    except json.JSONDecodeError:
        logger.warning("AI вернул невалидный JSON, повторяю с temperature=0")
        resp2 = await provider.chat(
            messages=messages, model=model, temperature=0.0, max_tokens=max_tokens
        )
        return _parse_json(resp2.content), resp2


async def generate_lesson_package(
    course_title: str,
    module_title: str,
    topic: str,
    level: str,
    duration_minutes: int,
    task_type: str = "code",
    language: str = "python",
) -> tuple[LessonPackageSchema, int]:
    """Возвращает (LessonPackageSchema, total_tokens)."""
    prompt = LESSON_PACKAGE_GENERATE.format(
        course_title=course_title,
        module_title=module_title,
        topic=topic,
        level=level,
        duration_minutes=duration_minutes,
        task_type=task_type,
        language=language,
    )
    data, resp = await _chat_with_retry(
        messages=[{"role": "user", "content": prompt}],
        model="pro",
        temperature=0.4,
        max_tokens=3072,
    )
    package = LessonPackageSchema.model_validate(data)
    return package, resp.total_tokens


async def check_task_submission(task, student_solution: str) -> tuple[dict, int]:
    """Проверяет решение через GigaChat-Max. Возвращает (result_dict, total_tokens)."""
    prompt = TASK_CHECK.format(
        task_description=task.description_md,
        requirements_json=json.dumps(task.requirements or [], ensure_ascii=False),
        criteria_json=json.dumps(task.check_criteria or [], ensure_ascii=False),
        passing_score=task.passing_score,
        reference_solution=task.reference_solution or "(нет эталона)",
        student_solution=student_solution,
    )
    data, resp = await _chat_with_retry(
        messages=[{"role": "user", "content": prompt}],
        model="max",
        temperature=0.2,
        max_tokens=1024,
    )
    return data, resp.total_tokens


__all__ = [
    "generate_lesson_package",
    "check_task_submission",
    "AIProviderNotConfigured",
]
