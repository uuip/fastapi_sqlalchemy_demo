from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.common.exceptions import ApiException
from app.common.schemas.response import ErrorResponse


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def _api(request: Request, exc: ApiException) -> JSONResponse:
        return JSONResponse(
            ErrorResponse(code=exc.status_code, msg=exc.msg).model_dump(),
            status_code=exc.status_code,
            headers=exc.headers,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, str):
            content = ErrorResponse(code=exc.status_code, msg=exc.detail).model_dump()
        else:
            content = ErrorResponse(
                code=exc.status_code,
                msg=HTTPStatus(exc.status_code).phrase,
                data=jsonable_encoder(exc.detail),
            ).model_dump()
        return JSONResponse(content, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        # field_validator-raised ValueError instances live inside ctx and break JSON
        # serialization later; jsonable_encoder coerces them to strings up front.
        errors = jsonable_encoder(exc.errors())
        logger.error("Request validation error: {} {}\n{}", request.method, request.url.path, errors)
        return JSONResponse(
            ErrorResponse(
                code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                msg="Request validation error",
                data=errors,
            ).model_dump(),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.opt(exception=exc).error(
            "Database operation error: {} {}: {}", request.method, request.url.path, exc
        )
        return JSONResponse(
            ErrorResponse(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg="Database operation failed").model_dump(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
