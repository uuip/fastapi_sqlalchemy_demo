from fastapi import Request
from fastapi.responses import JSONResponse

from .generic import Rsp


class ApiException(Exception):
    def __init__(self, msg: str, status_code: int = 400) -> None:
        super().__init__(msg)
        self.status_code = status_code
        self.err = Rsp(code=status_code, msg=msg)

    @staticmethod
    def handler(request: Request, exc: "ApiException") -> JSONResponse:
        return JSONResponse(exc.err.model_dump(), status_code=exc.status_code)
