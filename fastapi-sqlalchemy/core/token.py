from datetime import timedelta, datetime, timezone
from typing import Dict, Any, Optional

from jose import jwt
from pydantic import BaseModel

from config import settings

ALGORITHM = "HS256"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


def create_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> Token:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)
    return Token(access_token=encoded_jwt)


def decode_token(token):
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
