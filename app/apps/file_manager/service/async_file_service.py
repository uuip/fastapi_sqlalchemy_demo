import base64
import hashlib
import os
import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager, suppress
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models.errors import FileNotExistsError, FileTooLargeError
from ..models.file_record import FileRecord
from ..security.validator import FileValidator
from ..storage.base import AsyncStorage
from ..storage.enums import StorageType
from ..types.mime import detect_mime_type

_MIME_SNIFF_BYTES = 8192


def _sanitize_zip_entry_name(name: str) -> str:
    base = os.path.basename(name).strip() or "file"
    return base.replace("/", "_").replace("\\", "_")


def _dedupe_zip_entry_name(original_name: str, used_names: set[str]) -> str:
    if original_name not in used_names:
        return original_name
    stem, extension = os.path.splitext(original_name)
    suffix = 1
    while True:
        candidate = f"{stem} ({suffix}){extension}"
        if candidate not in used_names:
            return candidate
        suffix += 1


class AsyncFileService:
    def __init__(
        self,
        *,
        storage: AsyncStorage,
        session_factory: async_sessionmaker[AsyncSession],
        validator: FileValidator | None = None,
        storage_type: StorageType | str = StorageType.LOCAL,
        key_prefix: str = "upload_files",
    ):
        self._storage = storage
        self._storage_type = StorageType(storage_type)
        self._validator = validator or FileValidator()
        self._key_prefix = key_prefix
        self._session_maker = session_factory

    def _normalize_filename(self, filename: str) -> tuple[str, str]:
        if any(c in filename for c in ("/", "\\")):
            raise ValueError("Filename contains invalid characters")
        extension = os.path.splitext(filename)[1].lstrip(".").lower()
        if len(filename) > 200:
            filename = filename.split(".")[0][:200] + "." + extension
        return filename, extension

    async def upload_file(
        self,
        *,
        filename: str,
        content: bytes,
        mimetype: str,
        created_by: str = "",
    ) -> FileRecord:
        async def chunks() -> AsyncIterator[bytes]:
            yield content

        return await self.upload_stream(
            filename=filename,
            chunks=chunks(),
            mimetype=mimetype,
            created_by=created_by,
        )

    async def upload_stream(
        self,
        *,
        filename: str,
        chunks: AsyncIterator[bytes],
        mimetype: str,
        created_by: str = "",
    ) -> FileRecord:
        filename, extension = self._normalize_filename(filename)
        self._validator.validate_extension(extension)
        file_key = f"{self._key_prefix}/{uuid.uuid4()}.{extension}"
        size = 0
        digest = hashlib.sha3_256()
        sniff = bytearray()

        async def measured_chunks() -> AsyncIterator[bytes]:
            nonlocal size
            try:
                async for chunk in chunks:
                    if not chunk:
                        continue
                    size += len(chunk)
                    self._validator.validate_size(extension, size)
                    digest.update(chunk)
                    if len(sniff) < _MIME_SNIFF_BYTES:
                        sniff.extend(chunk[: _MIME_SNIFF_BYTES - len(sniff)])
                    yield chunk
            except FileTooLargeError:
                raise

        try:
            await self._storage.save_stream(file_key, measured_chunks())
        except FileTooLargeError:
            with suppress(Exception):
                await self._storage.delete(file_key)
            raise

        resolved_mime = detect_mime_type(bytes(sniff), filename=filename, client_mime=mimetype)

        record = FileRecord(
            storage_type=str(self._storage_type),
            key=file_key,
            name=filename,
            size=size,
            extension=extension,
            mime_type=resolved_mime,
            hash=digest.hexdigest(),
            created_by=created_by,
        )
        async with self._session_maker() as s:
            s.add(record)
            await s.commit()
            await s.refresh(record)
        return record

    async def upload_text(self, text: str, name: str, created_by: str = "") -> FileRecord:
        if len(name) > 200:
            name = name[:200]
        file_key = f"{self._key_prefix}/{uuid.uuid4()}.txt"
        content = text.encode("utf-8")

        await self._storage.save(file_key, content)

        record = FileRecord(
            storage_type=str(self._storage_type),
            key=file_key,
            name=name,
            size=len(content),
            extension="txt",
            mime_type="text/plain; charset=utf-8",
            hash=FileRecord.compute_hash(content),
            created_by=created_by,
        )
        async with self._session_maker() as s:
            s.add(record)
            await s.commit()
            await s.refresh(record)
        return record

    async def get_file(self, file_id: str) -> FileRecord:
        async with self._session_maker() as s:
            record = await s.get(FileRecord, file_id)
        if record is None:
            raise FileNotExistsError(f"File not found: {file_id}")
        return record

    async def get_file_base64(self, file_id: str) -> str:
        record = await self.get_file(file_id)
        blob = await self._storage.load_once(record.key)
        return base64.b64encode(blob).decode()

    async def get_file_content(self, file_id: str) -> str:
        record = await self.get_file(file_id)
        content = await self._storage.load_once(record.key)
        return content.decode("utf-8")

    async def get_file_stream(self, file_id: str) -> tuple[AsyncIterator[bytes], FileRecord]:
        record = await self.get_file(file_id)
        return self._storage.load_stream(record.key), record

    async def delete_file(self, file_id: str) -> bool:
        async with self._session_maker() as s:
            record = await s.get(FileRecord, file_id)
            if record is None:
                return False
            await self._storage.delete(record.key)
            await s.delete(record)
            await s.commit()
        return True

    async def get_files_by_ids(
        self, file_ids: Sequence[str], *, owner_id: str | None = None
    ) -> dict[str, FileRecord]:
        if not file_ids:
            return {}
        unique_ids = list({str(fid) for fid in file_ids})
        async with self._session_maker() as s:
            stmt = select(FileRecord).where(FileRecord.id.in_(unique_ids))
            if owner_id is not None:
                stmt = stmt.where(FileRecord.created_by == owner_id)
            records = (await s.scalars(stmt)).all()
        return {str(r.id): r for r in records}

    @asynccontextmanager
    async def build_zip(self, *, file_records: Sequence[FileRecord]) -> AsyncIterator[str]:
        used_names: set[str] = set()
        tmp_path: str | None = None
        try:
            with NamedTemporaryFile(mode="w+b", suffix=".zip", delete=False) as tmp:
                tmp_path = tmp.name
                with ZipFile(tmp, mode="w", compression=ZIP_DEFLATED) as zf:
                    for record in file_records:
                        safe_name = _sanitize_zip_entry_name(record.name)
                        arcname = _dedupe_zip_entry_name(safe_name, used_names)
                        used_names.add(arcname)
                        with zf.open(arcname, "w") as entry:
                            async for chunk in self._storage.load_stream(record.key):
                                entry.write(chunk)
                tmp.flush()

            assert tmp_path is not None
            yield tmp_path
        finally:
            if tmp_path is not None:
                with suppress(FileNotFoundError):
                    os.remove(tmp_path)
