from datetime import timedelta

from fastapi import HTTPException, APIRouter
from fastapi.security import HTTPBasicCredentials
from sqlalchemy import select
from starlette import status

from core.token import create_token, Token
from deps import SessionDep
from model import User
from response import Rsp, OK

token_api = APIRouter(prefix="/token", tags=["token管理"])


@token_api.post("/", response_model=Rsp[Token])
async def login(s: SessionDep, data: HTTPBasicCredentials) -> Token:
    e = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = await s.scalar(select(User).where(User.username == data.username))
    if not user:
        raise e
    user_status = user.check_password(data.password)
    if not user_status:
        raise e
    token_expires = timedelta(days=30)
    token = create_token(data={"id": user.id}, expires_delta=token_expires)
    return OK(token)
