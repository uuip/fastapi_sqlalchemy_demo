import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqladmin import Admin

from fastapi_sqlalchemy.admin import UserAdmin, authentication_backend
from fastapi_sqlalchemy.api.account import data_api
from fastapi_sqlalchemy.api.auth import token_api
from fastapi_sqlalchemy.api.param_examples import example_api
from fastapi_sqlalchemy.core.exception_handlers import install_exception_handlers
from fastapi_sqlalchemy.core.logging import setup_logging
from fastapi_sqlalchemy.deps.db import async_db


@contextlib.asynccontextmanager
async def lifespan_context(app: FastAPI):
    logger.debug("Application startup: initializing resources")
    # Initialize resources (database connections, caches, etc.)
    yield
    # Clean up resources (close connections, etc.)
    logger.debug("Application shutdown: cleaning up resources")


app = FastAPI(
    title="FastAPI SQLAlchemy Demo",
    description="A demonstration project using FastAPI with SQLAlchemy",
    version="1.0.0",
    lifespan=lifespan_context,
)

setup_logging()

# 必须在 add_middleware(CORSMiddleware) 之前调用，否则异常兜底的响应会绕过 CORS
install_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data_api)
app.include_router(token_api)
app.include_router(example_api)
admin = Admin(app, async_db, authentication_backend=authentication_backend)
admin.add_view(UserAdmin)


@app.post("/health", description="Health check")
@app.get("/health", description="Health check")
async def health():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    try:
        uvicorn.run(
            "fastapi_sqlalchemy.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
        )
    except KeyboardInterrupt:
        logger.info("Server is shutting down")
