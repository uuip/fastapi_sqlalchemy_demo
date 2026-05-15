from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.apps.accounts.models import User
from app.apps.accounts.services.auth import authenticate_token
from app.common.deps import SessionDep

type TokenDep = Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())]


async def authenticate(s: SessionDep, token: TokenDep) -> User:
    return await authenticate_token(s, token.credentials)


# 对象, dependencies=[...]
user_dep = Depends(authenticate)
# 声明类型，函数中参数定义
type UserDep = Annotated[User, Depends(authenticate)]
