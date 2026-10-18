"""Единый формат ошибок API: { error: { code, message } } + русские сообщения."""
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_response(code: str, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"error": {"code": code, "message": message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # detail может быть dict {code, message} или str
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            return error_response(
                code=exc.detail.get("code", "HTTP_ERROR"),
                message=exc.detail.get("message", "Ошибка"),
                http_status=exc.status_code,
            )
        code = _default_code_for_status(exc.status_code)
        message = exc.detail if isinstance(exc.detail, str) else "Ошибка"
        return error_response(code, message, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Берём первое сообщение, остальные кладём в details
        first = exc.errors()[0] if exc.errors() else {"msg": "Ошибка валидации"}
        msg = first.get("msg", "Ошибка валидации")
        # exc.errors() может содержать ValueError в ctx — пропускаем через
        # jsonable_encoder, чтобы получить JSON-сериализуемое представление.
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=jsonable_encoder({
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": msg,
                    "details": exc.errors(),
                }
            }),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        return error_response(
            code="INTERNAL_ERROR",
            message="Внутренняя ошибка сервера",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _default_code_for_status(http_status: int) -> str:
    return {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }.get(http_status, "HTTP_ERROR")
