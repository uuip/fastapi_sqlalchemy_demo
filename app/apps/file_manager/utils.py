from app.apps.file_manager.models.file_record import FileRecord
from app.apps.file_manager.security.signer import FileSigner

UploadResponse = dict[str, str | int]


def serialize_upload_record(record: FileRecord) -> UploadResponse:
    return {
        "id": record.id,
        "name": record.name,
        "size": record.size,
        "extension": record.extension,
        "mime_type": record.mime_type,
    }


def build_urls(signer: FileSigner, file_id: str) -> dict[str, str]:
    return {
        "preview": signer.sign_file(file_id),
        "download": signer.sign_file(file_id, as_attachment=True),
        "delete": signer.sign_file_delete(file_id),
    }


def serialize_upload_record_with_urls(
    record: FileRecord, signer: FileSigner
) -> dict[str, str | int | dict[str, str]]:
    payload = dict(serialize_upload_record(record))
    payload["urls"] = build_urls(signer, record.id)
    return payload
