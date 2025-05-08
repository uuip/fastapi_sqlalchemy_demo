import contextlib
import json
import time
from typing import Callable, Awaitable

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from sqladmin import Admin
from sqlalchemy.exc import SQLAlchemyError

from adminsite import UserAdmin, authentication_backend
from api.auth import token_api
from api.tree import data_api
from config import settings
from deps.db import async_db
from response import ERROR
from response.exceptions import ApiException
from utils import custom_openapi


@contextlib.asynccontextmanager
async def lifespan_context(app: FastAPI) -> None:
    logger.info("Application startup: initializing resources")
    # Initialize resources (database connections, caches, etc.)
    yield
    # Clean up resources (close connections, etc.)
    logger.info("Application shutdown: cleaning up resources")


if settings.debug:
    kwargs = {}
else:
    import api.docs  # noqa

    kwargs = dict(docs_url=None, redoc_url=None, openapi_url=None)

app = FastAPI(
    title="FastAPI SQLAlchemy Demo",
    description="A demonstration project using FastAPI with SQLAlchemy",
    version="1.0.0",
    lifespan=lifespan_context,
    **kwargs,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_api)
app.include_router(token_api)

admin = Admin(app, async_db, authentication_backend=authentication_backend)
admin.add_view(UserAdmin)

ApiException.register(app)
custom_openapi(app)


@app.middleware("http")
async def request_body_logging(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    if request.method in {"POST", "PUT", "PATCH"}:
        body_bytes = await request.body()
        try:
            body_json = json.loads(body_bytes)
            logger.info("Request body: {}", body_json)
        except json.JSONDecodeError:
            logger.info("Request body (non-JSON)")

    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.error(f"RequestValidationError: {exc.errors()}")
    return JSONResponse(ERROR(data=exc.errors()).model_dump(), status_code=400)


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    error_msg = ". ".join(exc.args)
    logger.error("Database operation error: {}", error_msg)
    return JSONResponse(ERROR(error_msg).model_dump(), status_code=500)


@app.get("/time", summary="Get current timestamp", description="Returns the current Unix timestamp in seconds")
async def get_current_timestamp() -> int:
    return int(time.time())


if __name__ == "__main__":
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            workers=2,
        )
    except KeyboardInterrupt:
        logger.info("Server is shutting down")
