from typing import Any

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import Text, TypeDecorator

password_hash = PasswordHash((Argon2Hasher(),))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def make_password(password: str) -> str:
    return password_hash.hash(password)


class PassWord(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Any) -> str | None:
        if value is None:
            return None
        return make_password(value)

    def process_result_value(self, value: str | None, dialect: Any) -> str | None:
        return value
