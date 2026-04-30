from sqlalchemy import *
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import *

from fastapi_sqlalchemy.core.password import PassWord, verify_password


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user"
    id = mapped_column(BigInteger, Identity(), primary_key=True)
    username = mapped_column(Text, nullable=False, unique=True)
    password = mapped_column(PassWord, nullable=False)
    updated_at = mapped_column(
        TIMESTAMP(timezone=True, precision=0),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    created_at = mapped_column(TIMESTAMP(timezone=True, precision=0), server_default=func.current_timestamp())
    balance = mapped_column(BigInteger)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"

    def check_password(self, password):
        return verify_password(password, self.password)
