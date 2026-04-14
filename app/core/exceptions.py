from fastapi import status


class ApiException(Exception):
    def __init__(
        self,
        msg: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(msg)
        self.msg = msg
        self.status_code = status_code
        self.headers = headers
