import contextlib
import time

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqladmin import Admin

from fastapi_sqlalchemy.adminsite import UserAdmin, authentication_backend
from fastapi_sqlalchemy.api.account import data_api
from fastapi_sqlalchemy.api.param_examples import example_api
from fastapi_sqlalchemy.api.auth import token_api
from fastapi_sqlalchemy.config import settings
from fastapi_sqlalchemy.deps.db import async_db
from fastapi_sqlalchemy.exception_handlers import install_exception_handlers
from fastapi_sqlalchemy.logging_config import setup_logging
from fastapi_sqlalchemy.utils import custom_openapi


@contextlib.asynccontextmanager
async def lifespan_context(app: FastAPI):
    logger.debug("Application startup: initializing resources")
    # Initialize resources (database connections, caches, etc.)
    yield
    # Clean up resources (close connections, etc.)
    logger.debug("Application shutdown: cleaning up resources")


if settings.debug:
    kwargs = {}
else:
    kwargs = dict(docs_url=None, redoc_url=None, openapi_url=None)

app = FastAPI(
    title="FastAPI SQLAlchemy Demo",
    description="A demonstration project using FastAPI with SQLAlchemy",
    version="1.0.0",
    lifespan=lifespan_context,
    **kwargs,
)

# Order matters: setup_logging registers the catch-all middleware which must
# sit INNER to CORSMiddleware. add_middleware uses insert(0), so the last
# registered middleware ends up outermost; error responses then exit through
# CORS and keep Access-Control-Allow-Origin even on 5xx.
setup_logging(app)

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
if not settings.debug:
    from fastapi_sqlalchemy.api.docs import docs_api

    app.include_router(docs_api)
admin = Admin(app, async_db, authentication_backend=authentication_backend)
admin.add_view(UserAdmin)
install_exception_handlers(app)
custom_openapi(app)


@app.get("/time", description="Returns the current Unix timestamp in seconds")
async def get_current_timestamp() -> int:
    return int(time.time())


@app.post("/health", description="Health check")
@app.get("/health", description="Health check")
async def health():
    return {"ok": True}


if __name__ == "__main__":
    try:
        uvicorn.run(
            "fastapi_sqlalchemy.main:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_config=None,
        )
    except KeyboardInterrupt:
        logger.info("Server is shutting down")
