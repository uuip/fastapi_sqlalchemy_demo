from datetime import timedelta

from fastapi import HTTPException, APIRouter
from fastapi.security import HTTPBasicCredentials
from sqlalchemy import select
from starlette import status

from fastapi_sqlalchemy.config import settings
from fastapi_sqlalchemy.core.token import create_token, Token
from fastapi_sqlalchemy.deps import SessionDep
from fastapi_sqlalchemy.model import User
from fastapi_sqlalchemy.response import Rsp, OK

token_api = APIRouter(prefix="/token", tags=["Token Management"])


@token_api.post(
    "/",
    response_model=Rsp[Token],
    summary="Login and get access token",
    description="Authenticate with username and password to receive a JWT token",
)
async def login(s: SessionDep, credentials: HTTPBasicCredentials) -> Rsp[Token]:
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = await s.scalar(select(User).where(User.username == credentials.username))
    if not user:
        raise auth_exception

    if not user.check_password(credentials.password):
        raise auth_exception

    token_expires = timedelta(days=settings.jwt_expire_days)
    token = create_token(data={"id": user.id}, expires_delta=token_expires)

    return OK(token)
