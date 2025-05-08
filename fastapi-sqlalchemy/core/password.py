from typing import Any, Optional

from passlib.context import CryptContext
from sqlalchemy import TypeDecorator, Text

pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def make_password(password: str) -> str:
    return pwd_context.hash(password)


class PassWord(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect: Any) -> Optional[str]:
        if value is None:
            return None
        return make_password(value)

    def process_result_value(self, value: Optional[str], dialect: Any) -> Optional[str]:
        return value
