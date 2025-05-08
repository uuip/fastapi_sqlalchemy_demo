from typing import TypeAlias, Annotated, Dict, Any

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy import select
from starlette import status

from core.token import decode_token
from deps.db import SessionDep
from model import User

security = HTTPBearer()
TokenDep: TypeAlias = Annotated[HTTPAuthorizationCredentials, Depends(security)]


async def authenticate(s: SessionDep, token: TokenDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload: Dict[str, Any] = decode_token(token.credentials)
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
