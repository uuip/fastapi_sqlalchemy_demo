from urllib.parse import quote

import pytest
from fastapi.responses import FileResponse

from app.api import files
from app.core.exceptions import ApiException


async def test_download_file_uses_fileresponse_filename_for_unicode_content_disposition(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "STATIC_DIR", tmp_path)
    filename = "报告.docx"
    file_path = tmp_path / filename
    file_path.write_bytes(b"document")

    response = await files.download_file(filename)

    assert isinstance(response, FileResponse)
    assert response.path == file_path
    assert response.headers["content-disposition"] == f"attachment; filename*=utf-8''{quote(filename)}"


@pytest.mark.parametrize("filename", ["../pyproject.toml", "/etc/passwd"])
async def test_download_file_rejects_paths_outside_static_dir(tmp_path, monkeypatch, filename):
    monkeypatch.setattr(files, "STATIC_DIR", tmp_path)

    with pytest.raises(ApiException) as exc_info:
        await files.download_file(filename)

    assert exc_info.value.status_code == 404
    assert exc_info.value.msg == "File not found"


async def test_download_file_rejects_directories(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "STATIC_DIR", tmp_path)
    (tmp_path / "folder").mkdir()

    with pytest.raises(ApiException) as exc_info:
        await files.download_file("folder")

    assert exc_info.value.status_code == 404
    assert exc_info.value.msg == "File not found"
