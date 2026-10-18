"""RBAC: иерархия admin > teacher > student.

require_role('teacher') пускает teacher и admin, но не student.
"""
from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User

ROLE_ORDER: dict[str, int] = {"student": 0, "teacher": 1, "admin": 2}

LEVELS_LE: dict[str, list[str]] = {
    "beginner": ["beginner"],
    "junior": ["beginner", "junior"],
    "middle": ["beginner", "junior", "middle"],
    "senior": ["beginner", "junior", "middle", "senior"],
}


def require_role(*roles: str):
    """Зависимость FastAPI: пускает пользователей с ролью >= минимальной из roles."""
    if not roles:
        raise ValueError("require_role: укажи хотя бы одну роль")
    min_required = min(ROLE_ORDER[r] for r in roles)

    async def dep(user: User = Depends(get_current_user)) -> User:
        if ROLE_ORDER.get(user.role, -1) < min_required:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        return user

    return dep


def has_role(user: User, *roles: str) -> bool:
    if not roles:
        return False
    min_required = min(ROLE_ORDER[r] for r in roles)
    return ROLE_ORDER.get(user.role, -1) >= min_required
