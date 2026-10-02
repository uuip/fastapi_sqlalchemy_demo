from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import ApiException
from app.core.logging import SENSITIVE_FIELDS, redact_data
from app.schemas.response import ErrorResponse
from app.utils import pretty_data


def _error_response(
    status_code: int,
    msg: str,
    *,
    data: Any = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        ErrorResponse(code=status_code, msg=msg, data=data).model_dump(),
        status_code=status_code,
        headers=headers,
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def _api(request: Request, exc: ApiException) -> JSONResponse:
        return _error_response(exc.status_code, exc.msg, headers=exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, str):
            msg = exc.detail
            data = None
        else:
            msg = HTTPStatus(exc.status_code).phrase
            data = jsonable_encoder(exc.detail)
        return _error_response(exc.status_code, msg, data=data, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        # field_validator-raised ValueError instances live inside ctx and break JSON
        # serialization later; jsonable_encoder coerces them to strings up front.
        errors = redact_data(jsonable_encoder(exc.errors()))
        for error in errors:
            if "input" in error and any(str(part).casefold() in SENSITIVE_FIELDS for part in error["loc"]):
                error["input"] = "***"
        logger.warning("Request validation error: {} {}\n{}", request.method, request.url.path, pretty_data(errors))
        return _error_response(status.HTTP_422_UNPROCESSABLE_CONTENT, "Request validation error", data=errors)

    @app.exception_handler(SQLAlchemyError)
    async def _db(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.opt(exception=exc).error("Database operation error: {} {}: {}", request.method, request.url.path, exc)
        return _error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, "Database operation failed")
