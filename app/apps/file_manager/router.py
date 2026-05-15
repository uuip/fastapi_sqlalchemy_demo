from collections.abc import AsyncIterator, Iterator
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.apps.accounts.deps import UserDep
from app.apps.file_manager.deps import FileServiceDep, FileSignerDep
from app.apps.file_manager.models import FileNotExistsError, FileRecord
from app.apps.file_manager.security import FileSigner, is_html_content
from app.apps.file_manager.service import AsyncFileService
from app.apps.file_manager.utils import build_urls, serialize_upload_record_with_urls
from app.common.schemas.response import default_router_responses, error_response

file_manager_api = APIRouter(prefix="/files", tags=["files"], responses=default_router_responses())
UPLOAD_CHUNK_SIZE = 1024 * 1024


def _verify(
    *,
    signer: FileSigner,
    file_id: str,
    kind: str,
    timestamp: str,
    nonce: str,
    sign: str,
) -> None:
    if not signer.verify_signature(file_id=file_id, kind=kind, timestamp=timestamp, nonce=nonce, sign=sign):
        raise HTTPException(403, "Invalid or expired signature")


def _stream_headers(record: FileRecord, *, as_attachment: bool, media_type: str | None = None) -> dict[str, str]:
    headers = {
        "Content-Type": media_type or "application/octet-stream",
        "X-Content-Type-Options": "nosniff",
    }
    if record.size > 0:
        headers["Content-Length"] = str(record.size)
    if as_attachment:
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(record.name)}"
    return headers


async def _open_stream(
    service: AsyncFileService,
    file_id: str,
) -> tuple[Iterator[bytes] | AsyncIterator[bytes], FileRecord]:
    try:
        return await service.get_file_stream(file_id)
    except FileNotExistsError:
        raise HTTPException(404, "File not found") from None


async def _read_upload_chunks(file: UploadFile) -> AsyncIterator[bytes]:
    while chunk := await file.read(UPLOAD_CHUNK_SIZE):
        yield chunk


@file_manager_api.post("/upload", status_code=201)
async def upload(
    user: UserDep,
    file: Annotated[UploadFile, File()],
    service: FileServiceDep,
    signer: FileSignerDep,
    created_by: Annotated[str, Form()] = "",
) -> dict[str, str | int | dict[str, str]]:
    try:
        record = await service.upload_stream(
            filename=file.filename or "unknown",
            chunks=_read_upload_chunks(file),
            mimetype=file.content_type or "application/octet-stream",
            created_by=created_by or str(user.id),
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    return serialize_upload_record_with_urls(record, signer)


@file_manager_api.get(
    "/{file_id}/urls",
    responses={status.HTTP_404_NOT_FOUND: error_response(status.HTTP_404_NOT_FOUND, "File not found")},
)
async def get_urls(
    file_id: str,
    _user: UserDep,
    service: FileServiceDep,
    signer: FileSignerDep,
) -> dict[str, str]:
    try:
        await service.get_file(file_id)
    except FileNotExistsError:
        raise HTTPException(404, "File not found") from None
    return build_urls(signer, file_id)


@file_manager_api.get(
    "/{file_id}/preview",
    responses={status.HTTP_404_NOT_FOUND: error_response(status.HTTP_404_NOT_FOUND, "File not found")},
)
async def preview(
    file_id: str,
    timestamp: str,
    nonce: str,
    sign: str,
    service: FileServiceDep,
    signer: FileSignerDep,
) -> StreamingResponse:
    _verify(signer=signer, file_id=file_id, kind="preview", timestamp=timestamp, nonce=nonce, sign=sign)
    stream, record = await _open_stream(service, file_id)

    if is_html_content(record.mime_type, record.name, f".{record.extension}"):
        # XSS guard: force download for HTML
        return StreamingResponse(stream, headers=_stream_headers(record, as_attachment=True))

    # Use the real mime type so the browser can inline-render
    # (images, PDFs, audio/video, plain text, etc.)
    return StreamingResponse(
        stream,
        headers=_stream_headers(record, as_attachment=False, media_type=record.mime_type or None),
    )


@file_manager_api.get(
    "/{file_id}/download",
    responses={status.HTTP_404_NOT_FOUND: error_response(status.HTTP_404_NOT_FOUND, "File not found")},
)
async def download(
    file_id: str,
    timestamp: str,
    nonce: str,
    sign: str,
    service: FileServiceDep,
    signer: FileSignerDep,
) -> StreamingResponse:
    _verify(signer=signer, file_id=file_id, kind="download", timestamp=timestamp, nonce=nonce, sign=sign)
    stream, record = await _open_stream(service, file_id)
    return StreamingResponse(stream, headers=_stream_headers(record, as_attachment=True))


@file_manager_api.post("/{file_id}/delete")
async def delete(
    file_id: str,
    timestamp: str,
    nonce: str,
    sign: str,
    service: FileServiceDep,
    signer: FileSignerDep,
) -> dict[str, bool]:
    _verify(signer=signer, file_id=file_id, kind="delete", timestamp=timestamp, nonce=nonce, sign=sign)
    await service.delete_file(file_id)
    return {"ok": True}
