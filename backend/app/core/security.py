"""JWT (HS256) + bcrypt-хеширование паролей."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


def _create_token(sub: str, ttl_seconds: int, token_type: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(sub),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "type": token_type,
        # jti делает каждую выдачу уникальной даже в пределах одной секунды,
        # иначе iat совпадёт и два токена окажутся бит-в-бит одинаковыми.
        "jti": secrets.token_urlsafe(8),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    return _create_token(
        sub=str(user_id),
        ttl_seconds=settings.JWT_ACCESS_TTL_SECONDS,
        token_type="access",
        extra={"role": role},
    )


def create_refresh_token(user_id: int) -> str:
    return _create_token(
        sub=str(user_id),
        ttl_seconds=settings.JWT_REFRESH_TTL_SECONDS,
        token_type="refresh",
    )


def decode_token(token: str) -> dict[str, Any]:
    """Декодирует JWT. Бросает jose.JWTError если токен невалиден или истёк."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])


def hash_refresh_token(token: str) -> str:
    """HMAC-SHA256(JWT_SECRET, token). bcrypt тут НЕ подходит — он обрезает
    вход на 72 байтах, а JWT обычно длиннее, и две выдачи в пределах ~10 сек
    имеют одинаковые первые 72 байта (различие лишь в последней цифре iat
    лежит за пределами окна). Это ломает refresh-rotation.

    HMAC-SHA256 с JWT_SECRET даёт фиксированный 64-символьный хеш, без
    ограничения по длине и устойчив к compromise БД без секрета."""
    return hmac.new(
        settings.JWT_SECRET.encode(), token.encode(), hashlib.sha256
    ).hexdigest()


def verify_refresh_token(token: str, token_hash: str) -> bool:
    if not token_hash:
        return False
    # Если в БД лежит ещё старый bcrypt-хеш ($2b$...), пытаемся через bcrypt.
    # При первой удачной верификации rotate перепишет на новый sha256-хеш.
    if token_hash.startswith("$2"):
        try:
            return pwd_context.verify(token, token_hash)
        except Exception:
            return False
    return hmac.compare_digest(hash_refresh_token(token), token_hash)


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "hash_refresh_token",
    "verify_refresh_token",
    "JWTError",
]
