"""Integration test: FastAPI file_manager router with AsyncFileService."""

import io
import os
import tempfile
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.apps.accounts.deps import authenticate
from app.apps.file_manager import AsyncFileService, Base, FileSigner, StorageType, create_storage
from app.apps.file_manager.deps import get_file_manager_context
from app.apps.file_manager.router import file_manager_api

# Minimal valid 1x1 PNG so libmagic recognizes image/png on upload.
MINIMAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000b49444154789c6360000200000500017a5eab3f0000000049454e44ae426082"
)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest_asyncio.fixture
async def fastapi_client(tmp_dir, monkeypatch):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_dir}/test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    storage = create_storage(StorageType.LOCAL, root_path=os.path.join(tmp_dir, "files"))
    signer = FileSigner(secret_key="test-secret", base_url="http://localhost")
    service = AsyncFileService(
        storage=storage,
        session_factory=factory,
        storage_type=StorageType.LOCAL,
    )

    @dataclass(frozen=True)
    class TestFileManagerContext:
        storage: object
        service: AsyncFileService
        signer: FileSigner

    app = FastAPI()
    app.include_router(file_manager_api)
    app.dependency_overrides[get_file_manager_context] = lambda: TestFileManagerContext(
        storage=storage,
        service=service,
        signer=signer,
    )
    app.dependency_overrides[authenticate] = lambda: type("User", (), {"id": "test-user"})()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, signer, service

    app.dependency_overrides.clear()
    await engine.dispose()


def _signed(url: str) -> dict:
    parsed = urlparse(url)
    p = parse_qs(parsed.query)
    return {"timestamp": p["timestamp"][0], "nonce": p["nonce"][0], "sign": p["sign"][0]}


class TestFastAPIAdapter:
    async def test_upload_and_preview(self, fastapi_client):
        client, signer, _ = fastapi_client

        resp = await client.post(
            "/files/upload",
            files={"file": ("test.txt", io.BytesIO("你好 fastapi".encode()), "text/plain")},
            data={"created_by": "user1"},
        )
        assert resp.status_code == 201
        data = resp.json()
        file_id = data["id"]
        assert data["name"] == "test.txt"
        # upload response should include signed URLs
        assert set(data["urls"].keys()) == {"preview", "download", "delete"}
        assert "/preview?" in data["urls"]["preview"]
        assert "/download?" in data["urls"]["download"]
        assert "/delete?" in data["urls"]["delete"]

        resp = await client.get(f"/files/{file_id}/preview", params=_signed(signer.sign_file(file_id)))
        assert resp.status_code == 200
        assert resp.content == "你好 fastapi".encode()
        # preview returns the real mime + detected charset
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"
        assert resp.headers.get("x-content-type-options") == "nosniff"

    async def test_urls_endpoint(self, fastapi_client):
        client, _, _ = fastapi_client

        resp = await client.post(
            "/files/upload",
            files={"file": ("note.txt", io.BytesIO(b"x"), "text/plain")},
        )
        file_id = resp.json()["id"]

        resp = await client.get(f"/files/{file_id}/urls")
        assert resp.status_code == 200
        urls = resp.json()
        assert set(urls.keys()) == {"preview", "download", "delete"}

    async def test_urls_404_on_missing_file(self, fastapi_client):
        client, _, _ = fastapi_client
        resp = await client.get("/files/no-such-id/urls")
        assert resp.status_code == 404

    async def test_preview_image_returns_real_mime_with_headers(self, fastapi_client):
        client, signer, _ = fastapi_client

        resp = await client.post(
            "/files/upload",
            files={"file": ("test.png", io.BytesIO(MINIMAL_PNG), "image/png")},
        )
        file_id = resp.json()["id"]

        resp = await client.get(f"/files/{file_id}/preview", params=_signed(signer.sign_file(file_id)))
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        # regression: headers must be present even on image branch
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("content-length") == str(len(MINIMAL_PNG))

    async def test_preview_html_forces_download(self, fastapi_client):
        client, signer, _ = fastapi_client

        resp = await client.post(
            "/files/upload",
            files={"file": ("page.html", io.BytesIO(b"<html></html>"), "text/html")},
        )
        file_id = resp.json()["id"]

        resp = await client.get(f"/files/{file_id}/preview", params=_signed(signer.sign_file(file_id)))
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/octet-stream"
        assert "attachment" in resp.headers.get("content-disposition", "")

    async def test_download_attaches_disposition(self, fastapi_client):
        client, signer, _ = fastapi_client

        resp = await client.post(
            "/files/upload",
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        file_id = resp.json()["id"]

        resp = await client.get(
            f"/files/{file_id}/download",
            params=_signed(signer.sign_file(file_id, as_attachment=True)),
        )
        assert resp.status_code == 200
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert "filename*=UTF-8''" in cd

    async def test_download_unicode_filename_encoded(self, fastapi_client):
        client, signer, _ = fastapi_client

        resp = await client.post(
            "/files/upload",
            files={"file": ("中文.txt", io.BytesIO(b"data"), "text/plain")},
        )
        file_id = resp.json()["id"]

        resp = await client.get(
            f"/files/{file_id}/download",
            params=_signed(signer.sign_file(file_id, as_attachment=True)),
        )
        cd = resp.headers.get("content-disposition", "")
        assert "%E4%B8%AD%E6%96%87.txt" in cd

    async def test_preview_content_length(self, fastapi_client):
        client, signer, _ = fastapi_client

        resp = await client.post(
            "/files/upload",
            files={"file": ("test.txt", io.BytesIO(b"hello fastapi"), "text/plain")},
        )
        file_id = resp.json()["id"]

        resp = await client.get(f"/files/{file_id}/preview", params=_signed(signer.sign_file(file_id)))
        assert resp.headers.get("content-length") == "13"

    async def test_upload_no_file_returns_422(self, fastapi_client):
        client, _, _ = fastapi_client
        resp = await client.post("/files/upload")
        assert resp.status_code == 422

    async def test_upload_invalid_filename_returns_400(self, fastapi_client):
        client, _, _ = fastapi_client
        resp = await client.post(
            "/files/upload",
            files={"file": ("bad/name.txt", io.BytesIO(b"x"), "text/plain")},
        )
        assert resp.status_code == 400

    async def test_invalid_signature_returns_403(self, fastapi_client):
        client, _, _ = fastapi_client
        resp = await client.get(
            "/files/nonexistent/preview",
            params={"timestamp": "0", "nonce": "x", "sign": "bad"},
        )
        assert resp.status_code == 403

    async def test_missing_file_returns_404(self, fastapi_client):
        client, signer, _ = fastapi_client
        # valid sig but the file_id does not exist
        resp = await client.get(
            "/files/nope-id/preview",
            params=_signed(signer.sign_file("nope-id")),
        )
        assert resp.status_code == 404

    async def test_delete_file(self, fastapi_client):
        client, signer, service = fastapi_client

        resp = await client.post(
            "/files/upload",
            files={"file": ("delete.txt", io.BytesIO(b"delete me"), "text/plain")},
        )
        file_id = resp.json()["id"]

        resp = await client.post(f"/files/{file_id}/delete", params=_signed(signer.sign_file_delete(file_id)))
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

        from app.apps.file_manager.models import FileNotExistsError
        with pytest.raises(FileNotExistsError):
            await service.get_file(file_id)

    async def test_delete_invalid_signature_returns_403(self, fastapi_client):
        client, _, _ = fastapi_client
        resp = await client.post(
            "/files/nonexistent/delete",
            params={"timestamp": "0", "nonce": "x", "sign": "bad"},
        )
        assert resp.status_code == 403

    async def test_delete_missing_is_idempotent(self, fastapi_client):
        client, signer, _ = fastapi_client
        resp = await client.post(
            "/files/missing-id/delete",
            params=_signed(signer.sign_file_delete("missing-id")),
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}
