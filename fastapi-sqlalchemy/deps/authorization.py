from datetime import timedelta, datetime, timezone
from typing import TypeAlias, Annotated

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from models import User
from .db import SessionDep

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30
# openssl rand -hex 32
SECRET_KEY = "ffe4145185fa7e499999592324c1fec9f01d17a595747d3442048846852f25b3"
# pwd_context = CryptContext(schemes=["bcrypt"])
pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
auth_dep = Depends(oauth2_scheme)
AuthDep: TypeAlias = Annotated[str | None, Depends(oauth2_scheme)]


class Token(BaseModel):
    access_token: str
    token_type: str


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def make_password(password):
    return pwd_context.hash(password)


async def authenticate_user(s: AsyncSession, username, password):
    user = await s.scalar(select(User).where(User.username == username))
    if not user:
        return False
    valid_user = verify_password(password, user.password)
    if not valid_user:
        return False
    return user


def create_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: AuthDep, s: SessionDep) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("id")
        if user_id is None:
            raise credentials_exception
        else:
            # do something
            ...
    except JWTError:
        raise credentials_exception
    user = await s.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise credentials_exception
    return user


# 对象, dependencies=[...]
user_dep = Depends(get_current_user)
# 声明类型，函数中参数定义
UserDep: TypeAlias = Annotated[User, Depends(get_current_user)]
