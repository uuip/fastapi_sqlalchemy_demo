from pathlib import Path
from types import TracebackType

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError

from fastapi_sqlalchemy.core.exceptions import ApiException
from fastapi_sqlalchemy.schemas.response import Rsp

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
IGNORED_TRACEBACK_FILES = {
    PACKAGE_ROOT / "core" / "logging.py",
    PACKAGE_ROOT / "core" / "exception_handlers.py",
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
            new_traceback, old_traceback.tb_frame, old_traceback.tb_lasti, old_traceback.tb_lineno
        )

    return type(exc), exc, new_traceback


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiException)
    async def _api(request: Request, exc: ApiException) -> JSONResponse:
        return JSONResponse(Rsp.error(code=exc.status_code, msg=exc.msg).model_dump(), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        logger.error("Request validation error: {} {}\n{}", request.method, request.url.path, exc.errors())
        return JSONResponse(
            Rsp.error(code=400, msg="Request validation error", data=exc.errors()).model_dump(), status_code=400
        )

    @app.exception_handler(SQLAlchemyError)
    async def _db(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.opt(exception=project_exception(exc)).error(
            "Database operation error: {} {}: {}", request.method, request.url.path, exc
        )
        return JSONResponse(Rsp.error(code=500, msg="Database operation failed").model_dump(), status_code=500)

    # 不能用 @app.exception_handler(Exception)，原因：
    # Starlette 会把 Exception handler 挂到 ServerErrorMiddleware（最外层），
    # 响应直接返回客户端，绕过 CORSMiddleware，CORS 头丢失。
    #
    # 用 middleware 做异常兜底，并且必须在 add_middleware(CORSMiddleware) 之前
    # 调用本函数。add_middleware 每次插入到 user_middleware[0]（外层），
    # 后加的 CORS 在外层包裹 catch-all，错误响应才能流经 CORS。
    #
    #   ServerErrorMiddleware        ← 最外层，不可移动
    #     CORSMiddleware              ← 后加，在外层
    #       本 middleware (catch-all)  ← 先加，在内层
    #         ExceptionMiddleware     ← 其他 exception_handler
    #           Router
    @app.middleware("http")
    async def _unhandled(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.opt(exception=project_exception(exc)).error(
                "Unhandled error: {} {}", request.method, request.url.path
            )
            return JSONResponse(Rsp.error(code=500, msg="Internal server error").model_dump(), status_code=500)
