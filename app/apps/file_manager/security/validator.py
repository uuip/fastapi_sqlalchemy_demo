from ..models.errors import BlockedFileExtensionError, FileTooLargeError
from ..types.constants import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, VIDEO_EXTENSIONS

__all__ = [
    "BlockedFileExtensionError",
    "FileTooLargeError",
    "FileValidator",
]


class FileValidator:
    def __init__(
        self,
        *,
        extension_blacklist: set[str] | None = None,
        max_file_size_mb: int = 15,
        max_image_size_mb: int = 10,
        max_video_size_mb: int = 100,
        max_audio_size_mb: int = 50,
    ):
        self._blacklist = frozenset(ext.lstrip(".").lower() for ext in (extension_blacklist or set()))
        self._max_file_size = max_file_size_mb * 1024 * 1024
        self._max_image_size = max_image_size_mb * 1024 * 1024
        self._max_video_size = max_video_size_mb * 1024 * 1024
        self._max_audio_size = max_audio_size_mb * 1024 * 1024

    def validate_extension(self, extension: str) -> None:
        ext = extension.lstrip(".").lower()
        if ext in self._blacklist:
            raise BlockedFileExtensionError(extension=ext)

    def validate_size(self, extension: str, size: int) -> None:
        ext = extension.lstrip(".").lower()
        limit = self._get_size_limit(ext)
        if size > limit:
            raise FileTooLargeError(message=f"File size ({size} bytes) exceeds limit ({limit} bytes)")

    def _get_size_limit(self, extension: str) -> int:
        if extension in IMAGE_EXTENSIONS:
            return self._max_image_size
        if extension in VIDEO_EXTENSIONS:
            return self._max_video_size
        if extension in AUDIO_EXTENSIONS:
            return self._max_audio_size
        return self._max_file_size

    def validate(self, extension: str, size: int) -> None:
        self.validate_extension(extension)
        self.validate_size(extension, size)
