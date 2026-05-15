"""Integration tests for async file manager service and storage."""

import base64
import hashlib
import hmac
import os
import tempfile
import zipfile
from urllib.parse import parse_qs, urlparse

import anyio
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.apps.file_manager import (
    AsyncFileService,
    Base,
    BlockedFileExtensionError,
    FileNotExistsError,
    FileTooLargeError,
    FileType,
    StorageType,
    create_storage,
    standardize_file_type,
)
from app.apps.file_manager.security import FileSigner, FileValidator
from app.apps.file_manager.security.html_safety import is_html_content

# --- fixtures: async -------------------------------------------------------

@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
async def async_engine(tmp_dir):
    eng = create_async_engine(f"sqlite+aiosqlite:///{tmp_dir}/async_test.db")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
def async_storage(tmp_dir):
    return create_storage(StorageType.LOCAL, root_path=os.path.join(tmp_dir, "async_files"))


@pytest.fixture
def async_file_service(async_storage, async_engine):
    factory = async_sessionmaker(bind=async_engine, expire_on_commit=False)
    return AsyncFileService(
        storage=async_storage,
        session_factory=factory,
        storage_type=StorageType.LOCAL,
    )


async def _chunks(chunks: list[bytes]):
    for chunk in chunks:
        yield chunk


# --- async tests -----------------------------------------------------------

class TestAsyncFileService:
    async def test_upload_and_get(self, async_file_service):
        record = await async_file_service.upload_file(
            filename="test.txt",
            content=b"hello async",
            mimetype="text/plain",
            created_by="user-1",
        )
        assert record.id
        assert record.size == 11
        assert record.hash == hashlib.sha3_256(b"hello async").hexdigest()

        fetched = await async_file_service.get_file(record.id)
        assert fetched.id == record.id

    async def test_upload_stream_saves_chunks_and_metadata(self, async_file_service):
        async def chunks():
            yield b"hello "
            yield b"stream"

        record = await async_file_service.upload_stream(
            filename="stream.txt",
            chunks=chunks(),
            mimetype="text/plain",
            created_by="stream-user",
        )

        assert record.size == len(b"hello stream")
        assert record.hash == hashlib.sha3_256(b"hello stream").hexdigest()
        assert record.created_by == "stream-user"
        assert await async_file_service.get_file_content(record.id) == "hello stream"

    async def test_upload_stream_removes_partial_object_when_size_limit_fails(self, async_storage, async_engine):
        class RecordingStorage:
            def __init__(self, wrapped):
                self._wrapped = wrapped
                self.saved_key = ""

            async def save(self, filename: str, data: bytes) -> None:
                self.saved_key = filename
                await self._wrapped.save(filename, data)

            async def save_stream(self, filename: str, chunks):
                self.saved_key = filename
                await self._wrapped.save_stream(filename, chunks)

            async def load_once(self, filename: str) -> bytes:
                return await self._wrapped.load_once(filename)

            def load_stream(self, filename: str):
                return self._wrapped.load_stream(filename)

            async def download(self, filename: str, target_filepath: str) -> None:
                await self._wrapped.download(filename, target_filepath)

            async def exists(self, filename: str) -> bool:
                return await self._wrapped.exists(filename)

            async def delete(self, filename: str) -> None:
                await self._wrapped.delete(filename)

            async def scan(self, path: str, files: bool = True, directories: bool = False) -> list[str]:
                return await self._wrapped.scan(path, files, directories)

        storage = RecordingStorage(async_storage)
        service = AsyncFileService(
            storage=storage,
            session_factory=async_sessionmaker(bind=async_engine, expire_on_commit=False),
            validator=FileValidator(max_file_size_mb=0),
            storage_type=StorageType.LOCAL,
        )

        async def chunks():
            yield b"x"

        with pytest.raises(FileTooLargeError):
            await service.upload_stream(filename="too-big.txt", chunks=chunks(), mimetype="text/plain")

        assert storage.saved_key
        assert not await async_storage.exists(storage.saved_key)

    async def test_get_file_content(self, async_file_service):
        record = await async_file_service.upload_file(
            filename="data.csv", content=b"x,y", mimetype="text/csv"
        )
        assert await async_file_service.get_file_content(record.id) == "x,y"

    async def test_get_file_base64(self, async_file_service):
        record = await async_file_service.upload_file(
            filename="bin.dat", content=b"\x00\x01", mimetype="application/octet-stream"
        )
        b64 = await async_file_service.get_file_base64(record.id)
        assert base64.b64decode(b64) == b"\x00\x01"

    async def test_get_file_stream(self, async_file_service):
        record = await async_file_service.upload_file(
            filename="s.txt", content=b"streaming", mimetype="text/plain"
        )
        stream, fetched = await async_file_service.get_file_stream(record.id)
        chunks = [chunk async for chunk in stream]
        assert b"".join(chunks) == b"streaming"
        assert fetched.id == record.id

    async def test_delete_file(self, async_file_service):
        record = await async_file_service.upload_file(
            filename="d.txt", content=b"bye", mimetype="text/plain"
        )
        deleted = await async_file_service.delete_file(record.id)
        assert deleted is True
        with pytest.raises(FileNotExistsError):
            await async_file_service.get_file(record.id)

    async def test_delete_nonexistent_returns_false(self, async_file_service):
        assert await async_file_service.delete_file("missing-id") is False

    async def test_delete_file_keeps_record_when_storage_delete_fails(self, async_storage, async_engine):
        class FailingDeleteStorage:
            def __init__(self, wrapped):
                self._wrapped = wrapped

            async def save(self, filename: str, data: bytes) -> None:
                await self._wrapped.save(filename, data)

            async def save_stream(self, filename: str, chunks):
                await self._wrapped.save_stream(filename, chunks)

            async def load_once(self, filename: str) -> bytes:
                return await self._wrapped.load_once(filename)

            def load_stream(self, filename: str):
                return self._wrapped.load_stream(filename)

            async def download(self, filename: str, target_filepath: str) -> None:
                await self._wrapped.download(filename, target_filepath)

            async def exists(self, filename: str) -> bool:
                return await self._wrapped.exists(filename)

            async def delete(self, filename: str) -> None:
                raise RuntimeError("storage delete failed")

            async def scan(self, path: str, files: bool = True, directories: bool = False) -> list[str]:
                return await self._wrapped.scan(path, files, directories)

        service = AsyncFileService(
            storage=FailingDeleteStorage(async_storage),
            session_factory=async_sessionmaker(bind=async_engine, expire_on_commit=False),
            storage_type=StorageType.LOCAL,
        )
        record = await service.upload_file(filename="keep.txt", content=b"keep", mimetype="text/plain")

        with pytest.raises(RuntimeError, match="storage delete failed"):
            await service.delete_file(record.id)

        assert (await service.get_file(record.id)).id == record.id

    async def test_upload_text(self, async_file_service):
        record = await async_file_service.upload_text("hello", "note.txt", created_by="u1")
        assert record.extension == "txt"
        assert await async_file_service.get_file_content(record.id) == "hello"

    async def test_get_files_by_ids_with_owner(self, async_file_service):
        r1 = await async_file_service.upload_file(
            filename="a.txt", content=b"a", mimetype="text/plain", created_by="owner"
        )
        r2 = await async_file_service.upload_file(
            filename="b.txt", content=b"b", mimetype="text/plain", created_by="other"
        )
        result = await async_file_service.get_files_by_ids([r1.id, r2.id], owner_id="owner")
        assert set(result.keys()) == {r1.id}

    async def test_get_files_by_ids_empty(self, async_file_service):
        assert await async_file_service.get_files_by_ids([]) == {}

    async def test_filename_with_slash_rejected(self, async_file_service):
        with pytest.raises(ValueError, match="invalid characters"):
            await async_file_service.upload_file(
                filename="bad/name.txt", content=b"x", mimetype="text/plain"
            )

    async def test_build_zip_is_async_context_manager(self, async_file_service):
        r1 = await async_file_service.upload_file(
            filename="a.txt", content=b"aaa", mimetype="text/plain"
        )
        r2 = await async_file_service.upload_file(
            filename="b.txt", content=b"bbb", mimetype="text/plain"
        )
        async with async_file_service.build_zip(file_records=[r1, r2]) as zip_path:
            with zipfile.ZipFile(zip_path) as zf:
                assert set(zf.namelist()) == {"a.txt", "b.txt"}
                assert zf.read("a.txt") == b"aaa"
                assert zf.read("b.txt") == b"bbb"

        assert not await anyio.Path(zip_path).exists()


# --- storage / validator / signer / misc ---------------------------------

class TestOpenDALStorage:
    async def test_local_storage_round_trip_stream_exists_delete_and_scan(self, tmp_dir):
        storage = create_storage(StorageType.LOCAL, root_path=os.path.join(tmp_dir, "scan"))

        await storage.save("a/b.txt", b"b")
        await storage.save("a/c.txt", b"c")
        await storage.save_stream("a/d.txt", _chunks([b"d", b"d"]))

        assert await storage.load_once("a/b.txt") == b"b"
        chunks = [chunk async for chunk in storage.load_stream("a/c.txt")]
        assert b"".join(chunks) == b"c"
        assert await storage.load_once("a/d.txt") == b"dd"
        assert await storage.exists("a/b.txt")
        assert not await storage.exists("nonexistent/key.txt")

        files = await storage.scan("a", files=True)
        assert set(files) == {"a/b.txt", "a/c.txt", "a/d.txt"}

        await storage.delete("a/b.txt")
        assert not await storage.exists("a/b.txt")

    async def test_missing_local_file_raises_file_not_found(self, tmp_dir):
        storage = create_storage(StorageType.LOCAL, root_path=os.path.join(tmp_dir, "missing"))

        with pytest.raises(FileNotFoundError):
            await storage.load_once("nope.txt")

        with pytest.raises(FileNotFoundError):
            _ = [chunk async for chunk in storage.load_stream("nope.txt")]


class TestAsyncOnlyExports:
    def test_sync_api_is_not_exported(self):
        import app.apps.file_manager as file_manager
        import app.apps.file_manager.service as service_module
        import app.apps.file_manager.storage as storage_module

        assert not hasattr(file_manager, "FileService")
        assert not hasattr(service_module, "FileService")
        assert not hasattr(storage_module, "BaseStorage")
        assert not hasattr(storage_module, "OpenDALStorage")
        assert not hasattr(storage_module, "S3Storage")


class TestFileValidator:
    def test_blacklist(self):
        v = FileValidator(extension_blacklist={"exe", "bat"})
        with pytest.raises(BlockedFileExtensionError):
            v.validate_extension("exe")
        v.validate_extension("txt")

    def test_size_limit(self):
        v = FileValidator(max_file_size_mb=1)
        v.validate_size("txt", 100)
        with pytest.raises(FileTooLargeError):
            v.validate_size("txt", 2 * 1024 * 1024)


class TestFileSigner:
    def _signature(self, *, secret_key: str, kind: str, file_id: str, timestamp: str, nonce: str) -> str:
        data_to_sign = f"{kind}|{file_id}|{timestamp}|{nonce}"
        digest = hmac.new(secret_key.encode(), data_to_sign.encode(), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode()

    def _parse(self, url: str) -> dict:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return {
            "path": parsed.path,
            "timestamp": params["timestamp"][0],
            "nonce": params["nonce"][0],
            "sign": params["sign"][0],
        }

    def test_sign_preview_default(self):
        signer = FileSigner(secret_key="k", base_url="http://localhost")
        parts = self._parse(signer.sign_file("file-123"))
        assert parts["path"].endswith("/preview")
        assert signer.verify_signature(
            file_id="file-123", kind="preview",
            timestamp=parts["timestamp"], nonce=parts["nonce"], sign=parts["sign"],
        )

    def test_sign_download(self):
        signer = FileSigner(secret_key="k", base_url="http://localhost")
        parts = self._parse(signer.sign_file("file-123", as_attachment=True))
        assert parts["path"].endswith("/download")
        assert signer.verify_signature(
            file_id="file-123", kind="download",
            timestamp=parts["timestamp"], nonce=parts["nonce"], sign=parts["sign"],
        )

    def test_sign_delete(self):
        signer = FileSigner(secret_key="k", base_url="http://localhost")
        parts = self._parse(signer.sign_file_delete("file-123"))
        assert parts["path"].endswith("/delete")
        assert signer.verify_signature(
            file_id="file-123", kind="delete",
            timestamp=parts["timestamp"], nonce=parts["nonce"], sign=parts["sign"],
        )

    def test_signed_url_encodes_query_params(self):
        signer = FileSigner(secret_key="k", base_url="http://localhost")
        url = signer.sign_file("file-123")
        parts = self._parse(url)

        assert "%3D" in urlparse(url).query
        assert signer.verify_signature(
            file_id="file-123", kind="preview",
            timestamp=parts["timestamp"], nonce=parts["nonce"], sign=parts["sign"],
        )

    def test_never_expires(self):
        signer = FileSigner(secret_key="k", base_url="http://localhost", access_timeout=None)
        parts = self._parse(signer.sign_file("file-1"))
        assert signer.verify_signature(
            file_id="file-1", kind="preview",
            timestamp=parts["timestamp"], nonce=parts["nonce"], sign=parts["sign"],
        )

    def test_invalid_signature(self):
        signer = FileSigner(secret_key="k", base_url="http://localhost")
        assert not signer.verify_signature(
            file_id="f", kind="preview", timestamp="0", nonce="x", sign="bad"
        )

    def test_kind_mismatch_fails(self):
        signer = FileSigner(secret_key="k", base_url="http://localhost")
        parts = self._parse(signer.sign_file("f"))
        # sign generated for preview, verify as download should fail
        assert not signer.verify_signature(
            file_id="f", kind="download",
            timestamp=parts["timestamp"], nonce=parts["nonce"], sign=parts["sign"],
        )

    def test_expired_timestamp_fails(self, monkeypatch):
        signer = FileSigner(secret_key="k", base_url="http://localhost", access_timeout=10)
        monkeypatch.setattr("app.apps.file_manager.security.signer.time.time", lambda: 100)
        parts = self._parse(signer.sign_file("f"))

        monkeypatch.setattr("app.apps.file_manager.security.signer.time.time", lambda: 111)

        assert not signer.verify_signature(
            file_id="f", kind="preview",
            timestamp=parts["timestamp"], nonce=parts["nonce"], sign=parts["sign"],
        )

    def test_invalid_timestamp_fails_without_error(self):
        signer = FileSigner(secret_key="k", base_url="http://localhost", access_timeout=10)
        sign = self._signature(secret_key="k", kind="preview", file_id="f", timestamp="not-int", nonce="n")

        assert not signer.verify_signature(
            file_id="f", kind="preview", timestamp="not-int", nonce="n", sign=sign
        )

    def test_tampered_signature_fails(self):
        signer = FileSigner(secret_key="k", base_url="http://localhost")
        parts = self._parse(signer.sign_file("f"))
        prefix = "B" if parts["sign"].startswith("A") else "A"
        tampered = prefix + parts["sign"][1:]

        assert not signer.verify_signature(
            file_id="f", kind="preview",
            timestamp=parts["timestamp"], nonce=parts["nonce"], sign=tampered,
        )


class TestHtmlSafety:
    def test_html_detection(self):
        assert is_html_content("text/html", None)
        assert is_html_content(None, "page.html")
        assert not is_html_content("text/plain", "doc.txt")


class TestMimeDetection:
    """detect_mime_type: libmagic > client_mime > extension > octet-stream."""

    def test_libmagic_overrides_misleading_client_mime(self):
        from app.apps.file_manager.types.mime import detect_mime_type
        pdf_header = b"%PDF-1.4 some content here"
        # client lies about the type; libmagic should win
        assert detect_mime_type(pdf_header, filename="x.png", client_mime="image/png") == "application/pdf"

    def test_falls_back_to_client_mime_when_libmagic_returns_octet(self):
        from app.apps.file_manager.types.mime import detect_mime_type
        # 4 bytes of nothing — libmagic can't sniff anything meaningful
        opaque = b"\x00\x00\x00\x00"
        assert (
            detect_mime_type(opaque, filename="data.bin", client_mime="application/vnd.custom")
            == "application/vnd.custom"
        )

    def test_falls_back_to_extension_when_no_other_signal(self):
        from app.apps.file_manager.types.mime import detect_mime_type
        opaque = b"\x00\x00\x00\x00"
        # No client mime and libmagic gave up → extension guess
        assert (
            detect_mime_type(opaque, filename="report.pdf", client_mime="application/octet-stream")
            == "application/pdf"
        )

    def test_final_fallback_is_octet_stream(self):
        from app.apps.file_manager.types.mime import detect_mime_type
        assert detect_mime_type(b"\x00", filename="noext", client_mime="") == "application/octet-stream"

    def test_text_mime_includes_utf8_charset(self):
        from app.apps.file_manager.types.mime import detect_mime_type
        utf8 = "你好世界，今天天气真好".encode()
        assert detect_mime_type(utf8, filename="x.txt", client_mime="text/plain") == "text/plain; charset=utf-8"

    def test_text_mime_charset_detected_from_bytes(self):
        from app.apps.file_manager.types.mime import detect_mime_type
        # ASCII bytes — charset-normalizer reports ascii
        result = detect_mime_type(b"hello world", filename="x.txt", client_mime="text/plain")
        assert result.startswith("text/plain")
        assert "charset=" in result

    def test_binary_mime_has_no_charset(self):
        from app.apps.file_manager.types.mime import detect_mime_type
        pdf = b"%PDF-1.4 some bytes"
        result = detect_mime_type(pdf, filename="x.pdf", client_mime="")
        assert result == "application/pdf"
        assert "charset" not in result


class TestFileTypeDetection:
    def test_standardize(self):
        assert standardize_file_type(extension="jpg") == FileType.IMAGE
        assert standardize_file_type(extension="mp4") == FileType.VIDEO
        assert standardize_file_type(extension="mp3") == FileType.AUDIO
        assert standardize_file_type(extension="pdf") == FileType.DOCUMENT
        assert standardize_file_type(mime_type="image/png") == FileType.IMAGE


class TestS3Storage:
    async def test_s3_storage_upload_download_stream_exists_delete(self, monkeypatch):
        from botocore.exceptions import ClientError

        from app.apps.file_manager.storage.s3_storage import AsyncS3Storage

        class Body:
            def __init__(self, data: bytes):
                self._data = data

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def read(self, amount: int | None = None) -> bytes:
                if amount is None:
                    return self._data
                chunk, self._data = self._data[:amount], self._data[amount:]
                return chunk

            async def iter_chunks(self, chunk_size: int = 1024):
                while chunk := await self.read(chunk_size):
                    yield chunk

        class Client:
            def __init__(self):
                self.objects: dict[str, bytes] = {}
                self.parts: list[bytes] = []
                self.deleted: list[str] = []
                self.head_bucket_calls = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def head_bucket(self, **kwargs):
                self.head_bucket_calls += 1
                return {}

            async def put_object(self, *, Bucket: str, Key: str, Body: bytes):
                self.objects[Key] = Body

            async def create_multipart_upload(self, *, Bucket: str, Key: str):
                return {"UploadId": "upload-1"}

            async def upload_part(
                self,
                *,
                Bucket: str,
                Key: str,
                UploadId: str,
                PartNumber: int,
                Body: bytes,
            ):
                self.parts.append(Body)
                return {"ETag": f"etag-{PartNumber}"}

            async def complete_multipart_upload(self, *, Bucket: str, Key: str, UploadId: str, MultipartUpload: dict):
                self.objects[Key] = b"".join(self.parts)

            async def abort_multipart_upload(self, *, Bucket: str, Key: str, UploadId: str):
                self.parts.clear()

            async def get_object(self, *, Bucket: str, Key: str):
                if Key not in self.objects:
                    raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
                return {"Body": Body(self.objects[Key])}

            async def head_object(self, *, Bucket: str, Key: str):
                if Key not in self.objects:
                    raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
                return {}

            async def delete_object(self, *, Bucket: str, Key: str):
                self.deleted.append(Key)
                self.objects.pop(Key, None)

        class Session:
            def __init__(self):
                self.client = Client()

            def create_client(self, *args, **kwargs):
                return self.client

        session = Session()
        monkeypatch.setattr("app.apps.file_manager.storage.s3_storage.get_session", lambda: session)

        storage = AsyncS3Storage(bucket_name="bucket", region="us-east-1")
        await storage.save("a.txt", b"abcdef")
        await storage.save_stream("b.txt", _chunks([b"abc", b"def"]))
        await storage.save_stream("large.txt", _chunks([b"x" * (6 * 1024 * 1024)]))

        assert session.client.head_bucket_calls == 1
        assert await storage.load_once("a.txt") == b"abcdef"
        assert await storage.load_once("b.txt") == b"abcdef"
        assert [len(part) for part in session.client.parts] == [5 * 1024 * 1024, 1024 * 1024]
        assert await storage.load_once("large.txt") == b"x" * (6 * 1024 * 1024)
        assert b"".join([chunk async for chunk in storage.load_stream("a.txt")]) == b"abcdef"
        assert await storage.exists("a.txt")
        assert not await storage.exists("missing.txt")

        await storage.delete("a.txt")
        assert session.client.deleted == ["a.txt"]
        assert not await storage.exists("a.txt")

    async def test_s3_storage_exists_reraises_non_not_found_errors(self, monkeypatch):
        from botocore.exceptions import ClientError

        from app.apps.file_manager.storage.s3_storage import AsyncS3Storage

        class Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def head_bucket(self, **kwargs):
                return {}

            async def head_object(self, *, Bucket: str, Key: str):
                raise ClientError({"Error": {"Code": "403"}}, "HeadObject")

        class Session:
            def create_client(self, *args, **kwargs):
                return Client()

        monkeypatch.setattr("app.apps.file_manager.storage.s3_storage.get_session", lambda: Session())

        storage = AsyncS3Storage(bucket_name="bucket")
        with pytest.raises(ClientError):
            await storage.exists("forbidden.txt")

    async def test_s3_storage_missing_key_raises_file_not_found(self, monkeypatch):
        from botocore.exceptions import ClientError

        from app.apps.file_manager.storage.s3_storage import AsyncS3Storage

        class Client:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def head_bucket(self, **kwargs):
                return {}

            async def get_object(self, **kwargs):
                raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")

        class Session:
            def create_client(self, *args, **kwargs):
                return Client()

        monkeypatch.setattr("app.apps.file_manager.storage.s3_storage.get_session", lambda: Session())

        storage = AsyncS3Storage(bucket_name="bucket")
        with pytest.raises(FileNotFoundError):
            await storage.load_once("missing.txt")
        with pytest.raises(FileNotFoundError):
            _ = [chunk async for chunk in storage.load_stream("missing.txt")]

    async def test_s3_storage_checks_bucket_before_download_operations(self, monkeypatch):
        from app.apps.file_manager.storage.s3_storage import AsyncS3Storage

        class Body:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def read(self, amount: int | None = None) -> bytes:
                return b""

            async def iter_chunks(self, chunk_size: int = 1024):
                if False:
                    yield b""

        class Client:
            def __init__(self):
                self.head_bucket_calls = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def head_bucket(self, **kwargs):
                self.head_bucket_calls += 1

            async def get_object(self, **kwargs):
                return {"Body": Body()}

        class Session:
            def __init__(self):
                self.client = Client()

            def create_client(self, *args, **kwargs):
                return self.client

        session = Session()
        monkeypatch.setattr("app.apps.file_manager.storage.s3_storage.get_session", lambda: session)

        storage = AsyncS3Storage(bucket_name="bucket")
        assert await storage.load_once("a.txt") == b""
        assert session.client.head_bucket_calls == 1

    async def test_s3_storage_creates_bucket_on_404_and_ignores_403(self, monkeypatch):
        from botocore.exceptions import ClientError

        from app.apps.file_manager.storage.s3_storage import AsyncS3Storage

        class Client:
            def __init__(self, code: str):
                self.code = code
                self.created: list[str] = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def head_bucket(self, *, Bucket: str):
                raise ClientError({"Error": {"Code": self.code}}, "HeadBucket")

            async def create_bucket(self, *, Bucket: str):
                self.created.append(Bucket)

        clients: list[Client] = []

        class Session:
            def __init__(self, code: str):
                self.code = code

            def create_client(self, *args, **kwargs):
                client = Client(self.code)
                clients.append(client)
                return client

        monkeypatch.setattr("app.apps.file_manager.storage.s3_storage.get_session", lambda: Session("404"))
        await AsyncS3Storage(bucket_name="created").ensure_bucket()
        assert clients[-1].created == ["created"]

        monkeypatch.setattr("app.apps.file_manager.storage.s3_storage.get_session", lambda: Session("403"))
        await AsyncS3Storage(bucket_name="forbidden").ensure_bucket()
        assert clients[-1].created == []

    def test_s3_config_usage(self):
        from app.apps.file_manager.config import FileManagerConfig

        cfg = FileManagerConfig(
            storage_type="s3",
            s3_endpoint="https://minio.example.com",
            s3_region="cn-north-1",
            s3_bucket_name="my-bucket",
            s3_access_key="minioadmin",
            s3_secret_key="minioadmin",
            s3_address_style="path",
        )
        assert cfg.storage_type == "s3"
        assert cfg.s3_address_style == "path"
