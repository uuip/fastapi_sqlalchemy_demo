from passlib.context import CryptContext
from sqlalchemy import TypeDecorator, Text

# pwd_context = CryptContext(schemes=["bcrypt"])
pwd_context = CryptContext(schemes=["django_pbkdf2_sha256"])


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def make_password(password):
    return pwd_context.hash(password)


class PassWord(TypeDecorator):
    impl = Text

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def process_bind_param(self, value, dialect):
        return make_password(value)

    def process_result_value(self, value, dialect):
        return value
