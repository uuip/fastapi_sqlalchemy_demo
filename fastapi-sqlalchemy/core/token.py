from datetime import timedelta, datetime, timezone

from jose import jwt
from pydantic import BaseModel

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30
# openssl rand -hex 32
SECRET_KEY = "ffe4145185fa7e499999592324c1fec9f01d17a595747d3442048846852f25b3"


class Token(BaseModel):
    access_token: str
    token_type: str


def create_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return Token(access_token=encoded_jwt, token_type="bearer")


def decode_token(token):
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
