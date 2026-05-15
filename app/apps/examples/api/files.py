from pathlib import Path

from fastapi import APIRouter, status
from fastapi.responses import FileResponse

from app.common.exceptions import ApiException
from app.common.schemas.response import default_router_responses, error_response

# Relative to the process working directory; matches main.py's StaticFiles(directory="static").
STATIC_DIR = Path("static")

file_api = APIRouter(prefix="/static-files", tags=["Static File Download"], responses=default_router_responses())


def _resolve_download_path(filename: str) -> Path:
    static_dir = STATIC_DIR.resolve()
    try:
        file_path = (static_dir / filename).resolve(strict=True)
    except (FileNotFoundError, OSError):
        raise ApiException(msg="File not found", status_code=status.HTTP_404_NOT_FOUND) from None

    if not file_path.is_relative_to(static_dir) or not file_path.is_file():
        raise ApiException(msg="File not found", status_code=status.HTTP_404_NOT_FOUND)

    return file_path


@file_api.get(
    "/download/{filename}",
    responses={status.HTTP_404_NOT_FOUND: error_response(status.HTTP_404_NOT_FOUND, "File not found")},
)
async def download_file(filename: str):
    file_path = _resolve_download_path(filename)
    return FileResponse(path=file_path, filename=filename)
