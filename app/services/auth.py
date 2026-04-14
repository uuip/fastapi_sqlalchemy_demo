from datetime import timedelta
from typing import Any

from fastapi import status
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ApiException
from app.core.token import Token, create_token, decode_token
from app.models import User


def credentials_exception(msg: str = "Could not validate credentials") -> ApiException:
    return ApiException(
        msg=msg,
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def login_user(s: AsyncSession, *, username: str, password: str) -> Token:
    auth_exception = credentials_exception("Incorrect username or password")
    user = await s.scalar(select(User).where(User.username == username))
    if not user:
        raise auth_exception
    if not user.check_password(password):
        raise auth_exception

    token_expires = timedelta(days=settings.jwt_expire_days)
    return create_token(data={"id": user.id}, expires_delta=token_expires)


async def authenticate_token(s: AsyncSession, token: str) -> User:
    auth_exception = credentials_exception()
    try:
        payload: dict[str, Any] = decode_token(token)
        user_id = payload.get("id")
        if user_id is None:
            raise auth_exception
    except PyJWTError:
        raise auth_exception from None

    user = await s.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise auth_exception
    return user
