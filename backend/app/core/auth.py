import uuid
from dataclasses import dataclass

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import decode_jwt_token
from app.models.user import User


@dataclass(slots=True)
class AuthContext:
    user: User
    access_token: str


async def require_auth(
    db: AsyncSession = Depends(get_db_session),
    access_token: str | None = Cookie(default=None, alias=settings.jwt_access_cookie_name),
) -> AuthContext:
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Требуется авторизация")

    try:
        payload = decode_jwt_token(access_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Некорректный тип токена")

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен без пользователя")

    try:
        user_id = uuid.UUID(user_id_raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный идентификатор пользователя") from exc

    user = await db.scalar(
        select(User).options(selectinload(User.distributor)).where(User.id == user_id)
    )
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден или деактивирован")

    return AuthContext(user=user, access_token=access_token)


async def require_admin(auth: AuthContext = Depends(require_auth)) -> AuthContext:
    if auth.user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Требуются права администратора")
    return auth


async def require_registration_complete(auth: AuthContext = Depends(require_auth)) -> AuthContext:
    if not auth.user.is_registration_complete:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Завершите первый вход: подтверждение телефона, смена пароля и согласия",
        )
    return auth
