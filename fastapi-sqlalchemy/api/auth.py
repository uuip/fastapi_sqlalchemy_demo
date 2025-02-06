from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, APIRouter
from fastapi.security import OAuth2PasswordRequestForm
from starlette import status

from deps import Token, SessionDep
from deps.authorization import authenticate_user, create_token

token = APIRouter(prefix="/token", tags=["token管理"])


@token.post("/")
async def login(s: SessionDep, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = await authenticate_user(s, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_expires = timedelta(days=30)
    token = create_token(data={"id": user.id}, expires_delta=token_expires)
    return Token(access_token=token, token_type="bearer")
