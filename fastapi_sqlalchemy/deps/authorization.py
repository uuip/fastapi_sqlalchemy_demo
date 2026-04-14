from typing import TypeAlias, Annotated, Dict, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from starlette import status

from fastapi_sqlalchemy.core.token import decode_token
from fastapi_sqlalchemy.model import User
from .db import SessionDep

TokenDep: TypeAlias = Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]


async def authenticate(s: SessionDep, token: TokenDep | str) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token_str = token.credentials if hasattr(token, "credentials") else token
        payload: Dict[str, Any] = decode_token(token_str)
        user_id = payload.get("id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await s.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_exception

    return user


# 对象, dependencies=[...]
user_dep = Depends(authenticate)
# 声明类型，函数中参数定义
UserDep: TypeAlias = Annotated[User, Depends(authenticate)]
