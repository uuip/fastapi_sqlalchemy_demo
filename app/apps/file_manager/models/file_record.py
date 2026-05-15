import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FileRecord(Base):
    __tablename__ = "file_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    storage_type: Mapped[str] = mapped_column(String(32), nullable=False)
    key: Mapped[str] = mapped_column(String(512), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    extension: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    created_by: Mapped[str] = mapped_column(String(36), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC))

    @staticmethod
    def compute_hash(data: bytes) -> str:
        return hashlib.sha3_256(data).hexdigest()

    def __repr__(self) -> str:
        return f"<FileRecord {self.id} name={self.name!r}>"
