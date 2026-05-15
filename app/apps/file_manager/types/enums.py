from enum import StrEnum


class FileType(StrEnum):
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    CUSTOM = "custom"


class FileTransferMethod(StrEnum):
    LOCAL_FILE = "local_file"
    REMOTE_URL = "remote_url"
