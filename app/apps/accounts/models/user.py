from datetime import datetime

from sqlalchemy import BigInteger, Identity, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.apps.accounts.models.base import Base
from app.common.security.password import PassWord, verify_password


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column(Text, unique=True)
    password: Mapped[str] = mapped_column(PassWord, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True, precision=0),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True, precision=0),
        server_default=func.current_timestamp(),
    )
    energy: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0", nullable=False)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.id}>"

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password)
