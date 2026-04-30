from pathlib import Path
from types import TracebackType

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from fastapi_sqlalchemy.exceptions import ApiException
from fastapi_sqlalchemy.response import Rsp
from fastapi_sqlalchemy.utils import pretty_data

PACKAGE_ROOT = Path(__file__).resolve().parent
IGNORED_TRACEBACK_FILES = {
    PACKAGE_ROOT / "logging_config.py",
    PACKAGE_ROOT / "exception_handlers.py",
}


def project_exception(exc: BaseException) -> tuple[type[BaseException], BaseException, TracebackType | None]:
    traceback = exc.__traceback__
    project_frames = []
    non_ignored_frames = []
    while traceback is not None:
        filename = Path(traceback.tb_frame.f_code.co_filename).resolve()
        if filename not in IGNORED_TRACEBACK_FILES:
            non_ignored_frames.append(traceback)
            if filename.is_relative_to(PACKAGE_ROOT):
                project_frames.append(traceback)
        traceback = traceback.tb_next

    selected = project_frames or non_ignored_frames

    new_traceback = None
    for old_traceback in reversed(selected):
        new_traceback = TracebackType(
            new_traceback,
            old_traceback.tb_frame,
            old_traceback.tb_lasti,
            old_traceback.tb_lineno,
        )

    return type(exc), exc, new_traceback


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def _api(request: Request, exc: ApiException) -> JSONResponse:
        return JSONResponse(
            Rsp.error(code=exc.status_code, msg=exc.msg).model_dump(),
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.error(
            "Request validation error: {} {}\n{}",
            request.method,
            request.url.path,
            pretty_data(exc.errors()),
        )
        return JSONResponse(
            Rsp.error(code=400, msg="Request validation error", data=exc.errors()).model_dump(),
            status_code=400,
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.opt(exception=project_exception(exc)).error(
            "Database operation error: {} {}: {}",
            request.method,
            request.url.path,
            exc,
        )
        return JSONResponse(Rsp.error(code=500, msg="Database operation failed").model_dump(), status_code=500)

    # Catch-all sits in the user-middleware layer so error responses still flow
    # through CORSMiddleware. Starlette routes @app.exception_handler(Exception)
    # to ServerErrorMiddleware, which writes the response directly to the ASGI
    # server and bypasses user middleware (CORS headers would be lost).
    @app.middleware("http")
    async def _unhandled(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.opt(exception=project_exception(exc)).error(
                "Unhandled error: {} {}",
                request.method,
                request.url.path,
            )
            return JSONResponse(
                Rsp.error(code=500, msg="Internal server error").model_dump(),
                status_code=500,
            )
