from typing import Self, Any

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from .generic import Rsp


class ApiException(Exception):
    def __init__(self, msg: str, *args: Any) -> None:
        super().__init__(*args)
        self.err = Rsp(code=400, msg=msg)

    @classmethod
    def handler(cls, request: Request, exc: Self) -> Response:
        return JSONResponse(exc.err.model_dump())

    @classmethod
    def register(cls, app: FastAPI):
        app.add_exception_handler(cls, cls.handler)
