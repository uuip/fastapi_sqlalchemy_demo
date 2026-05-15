import base64
import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass
class FileSigner:
    secret_key: str
    base_url: str
    access_timeout: int | None = None  # seconds, None means never expire

    def sign_file(self, file_id: str, *, as_attachment: bool = False) -> str:
        kind = "download" if as_attachment else "preview"
        return self._build_signed_url(file_id, kind=kind)

    def sign_file_delete(self, file_id: str) -> str:
        return self._build_signed_url(file_id, kind="delete")

    def verify_signature(self, *, file_id: str, kind: str, timestamp: str, nonce: str, sign: str) -> bool:
        data_to_sign = f"{kind}|{file_id}|{timestamp}|{nonce}"
        expected = hmac.new(self.secret_key.encode(), data_to_sign.encode(), hashlib.sha256).digest()
        expected_encoded = base64.urlsafe_b64encode(expected).decode()

        if not hmac.compare_digest(sign, expected_encoded):
            return False

        if self.access_timeout is None:
            return True

        try:
            created_at = int(timestamp)
        except ValueError:
            return False
        return int(time.time()) - created_at <= self.access_timeout

    def _build_signed_url(self, file_id: str, *, kind: str) -> str:
        url = f"{self.base_url}/files/{file_id}/{kind}"
        timestamp = str(int(time.time()))
        nonce = os.urandom(16).hex()
        data_to_sign = f"{kind}|{file_id}|{timestamp}|{nonce}"
        sign = hmac.new(self.secret_key.encode(), data_to_sign.encode(), hashlib.sha256).digest()
        encoded_sign = base64.urlsafe_b64encode(sign).decode()
        query = urlencode({"timestamp": timestamp, "nonce": nonce, "sign": encoded_sign})
        return f"{url}?{query}"
