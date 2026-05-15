from dataclasses import dataclass

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.apps.file_manager import deps as file_manager_deps
from app.apps.file_manager import router as file_manager
from app.apps.file_manager.models import FileNotExistsError, FileRecord


class FakeSigner:
    def sign_file(self, file_id: str, *, as_attachment: bool = False) -> str:
        kind = "download" if as_attachment else "preview"
        return f"http://test/files/{file_id}/{kind}"

    def sign_file_delete(self, file_id: str) -> str:
        return f"http://test/files/{file_id}/delete"

    def verify_signature(self, *, file_id: str, kind: str, timestamp: str, nonce: str, sign: str) -> bool:
        return sign == f"{kind}:{file_id}"


class FakeService:
    def __init__(self, record: FileRecord | None = None):
        self.record = record
        self.opened: list[str] = []

    async def get_file_stream(self, file_id: str):
        self.opened.append(file_id)
        if self.record is None:
            raise FileNotExistsError(f"File not found: {file_id}")

        async def stream():
            yield b"content"

        return stream(), self.record


class FakeUploadService:
    def __init__(self):
        self.chunks = b""

    async def upload_stream(self, *, filename: str, chunks, mimetype: str, created_by: str = ""):
        self.filename = filename
        self.mimetype = mimetype
        self.created_by = created_by
        self.chunks = b"".join([chunk async for chunk in chunks])
        return _record(name=filename, mime_type=mimetype)


class FakeUploadFile:
    filename = "stream.txt"
    content_type = "text/plain"

    def __init__(self):
        self._chunks = [b"abc", b"def", b""]
        self.read_sizes: list[int] = []

    async def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        return self._chunks.pop(0)


class FakeUser:
    id = "user-1"


@dataclass
class FakeContext:
    service: FakeService
    signer: FakeSigner


def _record(*, mime_type: str = "text/plain", name: str = "test.txt", extension: str = "txt") -> FileRecord:
    return FileRecord(
        id="file-1",
        storage_type="local",
        key="upload_files/file-1.txt",
        name=name,
        size=7,
        extension=extension,
        mime_type=mime_type,
        hash="hash",
        created_by="user-1",
    )


async def test_download_uses_injected_file_manager_context():
    service = FakeService(_record())
    signer = FakeSigner()

    response = await file_manager.download(
        "file-1",
        timestamp="1",
        nonce="abc",
        sign="download:file-1",
        service=service,
        signer=signer,
    )

    assert isinstance(response, StreamingResponse)
    assert service.opened == ["file-1"]
    assert response.headers["content-disposition"] == "attachment; filename*=UTF-8''test.txt"


async def test_download_rejects_invalid_signature_before_opening_stream():
    service = FakeService(_record())
    signer = FakeSigner()

    with pytest.raises(HTTPException) as exc_info:
        await file_manager.download(
            "file-1",
            timestamp="1",
            nonce="abc",
            sign="bad",
            service=service,
            signer=signer,
        )

    assert exc_info.value.status_code == 403
    assert service.opened == []


def test_file_service_and_signer_dependencies_are_derived_from_context():
    service = FakeService(_record())
    signer = FakeSigner()
    context = FakeContext(service=service, signer=signer)

    assert file_manager_deps.get_file_service(context) is service
    assert file_manager_deps.get_file_signer(context) is signer


def test_file_manager_context_dependency_reads_request_app_state():
    app = FastAPI()
    context = object()
    app.state.file_manager_context = context

    request = Request(
        {
            "type": "http",
            "app": app,
            "headers": [],
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        }
    )

    assert file_manager_deps.get_file_manager_context(request) is context


def test_create_app_does_not_initialize_file_manager_context(monkeypatch):
    from app import main

    def fail_create_file_manager_context(**kwargs):
        raise AssertionError("file_manager context should not be created at app startup")

    monkeypatch.setattr(main, "create_file_manager_context", fail_create_file_manager_context, raising=False)

    main.create_app(include_admin=False)


async def test_lifespan_initializes_file_manager_context_on_app_state(monkeypatch):
    from app import main

    calls = []
    context = object()

    class DummyDb:
        async def dispose(self):
            calls.append("dispose")

    def fake_create_file_manager_context(**kwargs):
        calls.append(kwargs)
        return context

    monkeypatch.setattr(main, "async_db", DummyDb())
    monkeypatch.setattr(main, "create_file_manager_context", fake_create_file_manager_context, raising=False)

    app = FastAPI()
    async with main.lifespan_context(app):
        assert app.state.file_manager_context is context
        assert calls == [{"config": file_manager_deps.file_manager_config}]

    assert calls == [{"config": file_manager_deps.file_manager_config}, "dispose"]


async def test_stream_headers_do_not_advertise_ranges_for_streaming_audio_video():
    headers = file_manager._stream_headers(
        _record(mime_type="video/mp4", name="video.mp4", extension="mp4"),
        as_attachment=True,
    )

    assert "Accept-Ranges" not in headers


async def test_upload_reads_upload_file_in_chunks():
    service = FakeUploadService()
    upload_file = FakeUploadFile()

    response = await file_manager.upload(
        user=FakeUser(),
        file=upload_file,
        service=service,
        signer=FakeSigner(),
    )

    assert service.chunks == b"abcdef"
    assert service.created_by == "user-1"
    assert upload_file.read_sizes == [file_manager.UPLOAD_CHUNK_SIZE] * 3
    assert response["name"] == "stream.txt"
