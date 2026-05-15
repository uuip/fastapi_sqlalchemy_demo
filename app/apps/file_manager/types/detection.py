import mimetypes

from .constants import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS
from .enums import FileType


def standardize_file_type(*, extension: str = "", mime_type: str = "") -> FileType:
    if extension:
        ext = extension.lstrip(".").lower()
        if ext in IMAGE_EXTENSIONS:
            return FileType.IMAGE
        if ext in VIDEO_EXTENSIONS:
            return FileType.VIDEO
        if ext in AUDIO_EXTENSIONS:
            return FileType.AUDIO

    if mime_type:
        ft = get_file_type_by_mime_type(mime_type)
        if ft != FileType.CUSTOM:
            return ft

    if extension:
        return FileType.DOCUMENT

    return FileType.CUSTOM


def get_file_type_by_mime_type(mime_type: str) -> FileType:
    if not mime_type:
        return FileType.CUSTOM

    mime_lower = mime_type.lower()
    if mime_lower.startswith("image/"):
        return FileType.IMAGE
    if mime_lower.startswith("video/"):
        return FileType.VIDEO
    if mime_lower.startswith("audio/"):
        return FileType.AUDIO

    document_mimes = {
        "text/plain",
        "text/html",
        "text/markdown",
        "text/csv",
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    if mime_lower in document_mimes:
        return FileType.DOCUMENT

    guessed_type, _ = mimetypes.guess_type(f"file.{mime_lower.split('/')[-1]}")
    if guessed_type:
        if guessed_type.startswith("image/"):
            return FileType.IMAGE
        if guessed_type.startswith("video/"):
            return FileType.VIDEO
        if guessed_type.startswith("audio/"):
            return FileType.AUDIO

    return FileType.CUSTOM
