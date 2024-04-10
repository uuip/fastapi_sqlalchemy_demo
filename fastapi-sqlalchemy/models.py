from sqlalchemy import *
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import *

from settings import settings


class Base(DeclarativeBase):
    pass


class Trees(Base):
    __tablename__ = "trees"
    id = Column(BigInteger, Identity(), primary_key=True)
    energy = Column(BigInteger)
    updated_at = Column(
        TIMESTAMP(timezone=True, precision=0),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    created_at = Column(
        TIMESTAMP(timezone=True, precision=0),
        server_default=func.current_timestamp(),
    )

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"


class User(Base):
    __tablename__ = "user"
    id = Column(BigInteger, Identity(), primary_key=True)
    username = Column(Text, nullable=False, unique=True)
    password = Column(Text, nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True, precision=0),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    created_at = Column(
        TIMESTAMP(timezone=True, precision=0),
        server_default=func.current_timestamp(),
    )

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.id}>"


if __name__ == "__main__":
    db = create_engine(settings.db)
    Base.metadata.create_all(bind=db)
