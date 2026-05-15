import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger
from sqladmin import Admin

from app.apps.accounts.admin import UserAdmin, authentication_backend
from app.apps.file_manager.config import settings as file_manager_config
from app.apps.file_manager.deps import create_file_manager_context
from app.common.config import settings
from app.common.db import async_db
from app.common.exception_handlers import install_exception_handlers
from app.common.logging import setup_logging
from app.common.middleware import CatchAllExceptionMiddleware
from app.routing import api_router


@contextlib.asynccontextmanager
async def lifespan_context(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        stack.push_async_callback(async_db.dispose)
        app.state.file_manager_context = create_file_manager_context(config=file_manager_config)
        yield


async def health():
    return {"ok": True}


def register_middleware(app: FastAPI) -> None:
    install_exception_handlers(app)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    # Register before CORSMiddleware so CORS wraps it and 500 responses keep CORS headers.
    app.add_middleware(CatchAllExceptionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def register_routes(app: FastAPI) -> None:
    app.include_router(api_router)
    app.add_api_route("/health", health, methods=["GET"], description="Health check")
    app.add_api_route("/health", health, methods=["POST"], description="Health check")


def register_static_files(app: FastAPI) -> None:
    app.mount("/static", StaticFiles(directory="static"), name="static")


def register_admin(app: FastAPI) -> None:
    admin = Admin(app, async_db, authentication_backend=authentication_backend)
    admin.add_view(UserAdmin)


def create_app(*, openapi_url: str | None = settings.openapi_url, include_admin: bool = True) -> FastAPI:
    app = FastAPI(
        title="FastAPI SQLAlchemy Demo",
        description="A demonstration project using FastAPI with SQLAlchemy",
        version="1.0.0",
        lifespan=lifespan_context,
        openapi_url=openapi_url,
    )
    setup_logging()
    register_middleware(app)
    register_routes(app)
    register_static_files(app)
    if include_admin:
        register_admin(app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
        )
    except KeyboardInterrupt:
        logger.info("Server is shutting down")
