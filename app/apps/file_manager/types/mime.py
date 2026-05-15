"""MIME type & charset detection.

For text/* types we append a `charset=...` parameter detected by
charset-normalizer so browsers render non-ASCII (Chinese, Japanese, …) correctly.

Priority:
  1. libmagic (python-magic) sniffs the actual file header — most reliable, can
     catch clients that mislabel or claim octet-stream.
  2. Fallback to the client-supplied Content-Type (still useful when libmagic
     returns application/octet-stream for ambiguous binaries).
  3. Fallback to mimetypes.guess_type by extension.
  4. Finally application/octet-stream.

For text mime types, charset-normalizer chooses the most likely encoding from
the actual bytes; falls back to utf-8 if undetected.
"""

import mimetypes

import magic
from charset_normalizer import from_bytes

_OCTET_STREAM = "application/octet-stream"


def detect_mime_type(content: bytes, *, filename: str = "", client_mime: str = "") -> str:
    mime = _resolve_mime(content, filename=filename, client_mime=client_mime)
    if mime.startswith("text/") and "charset=" not in mime:
        charset = detect_charset(content) or "utf-8"
        return f"{mime}; charset={charset}"
    return mime


def detect_charset(content: bytes) -> str | None:
    """Detect text encoding using charset-normalizer; None if undetectable."""
    if not content:
        return None
    best = from_bytes(content).best()
    if best is None:
        return None
    return best.encoding.replace("_", "-")


def _resolve_mime(content: bytes, *, filename: str, client_mime: str) -> str:
    sniffed = _sniff(content)
    if sniffed and sniffed != _OCTET_STREAM:
        return sniffed

    if client_mime and client_mime != _OCTET_STREAM:
        return client_mime

    if filename:
        guessed, _ = mimetypes.guess_type(filename)
        if guessed:
            return guessed

    return sniffed or client_mime or _OCTET_STREAM


def _sniff(content: bytes) -> str:
    try:
        return magic.from_buffer(content, mime=True) or ""
    except magic.MagicException:
        return ""
