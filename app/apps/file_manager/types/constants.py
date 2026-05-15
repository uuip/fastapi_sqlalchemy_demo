def _with_case_variants(extensions: frozenset[str]) -> frozenset[str]:
    return extensions | {e.upper() for e in extensions}


IMAGE_EXTENSIONS: frozenset[str] = _with_case_variants(frozenset({"jpg", "jpeg", "png", "webp", "gif", "svg"}))

VIDEO_EXTENSIONS: frozenset[str] = _with_case_variants(frozenset({"mp4", "mov", "mpeg", "webm"}))

AUDIO_EXTENSIONS: frozenset[str] = _with_case_variants(frozenset({"mp3", "m4a", "wav", "amr", "mpga"}))

DOCUMENT_EXTENSIONS: frozenset[str] = frozenset(
    {
        "txt",
        "markdown",
        "md",
        "mdx",
        "pdf",
        "html",
        "htm",
        "xlsx",
        "xls",
        "docx",
        "csv",
        "pptx",
    }
    | {
        e.upper()
        for e in {
            "txt",
            "markdown",
            "md",
            "mdx",
            "pdf",
            "html",
            "htm",
            "xlsx",
            "xls",
            "docx",
            "csv",
            "pptx",
        }
    }
)

DEFAULT_MIME_TYPE = "application/octet-stream"
DEFAULT_EXTENSION = ".bin"

AUDIO_VIDEO_MIME_TYPES: frozenset[str] = frozenset(
    {
        "audio/mpeg",
        "audio/wav",
        "audio/mp4",
        "audio/ogg",
        "audio/flac",
        "audio/aac",
        "audio/x-m4a",
        "video/mp4",
        "video/webm",
        "video/quicktime",
    }
)
