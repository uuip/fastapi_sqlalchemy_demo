import contextlib
import logging
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqladmin import Admin
from sqlalchemy.exc import SQLAlchemyError

from adminsite import UserAdmin, authentication_backend
from api.auth import token_api
from api.tree import data_api
from config import settings
from deps.db import async_db
from response import ERROR, ErrRsp
from response.exceptions import ApiException
from utils import custom_openapi


@contextlib.asynccontextmanager
async def task(app):
    print("Run at startup!")
    yield
    print("Run on shutdown!")


# 指定当http状态码==422时，返回ErrRsp模型；使docs正确渲染
responses = {400: {"model": ErrRsp}}
if settings.debug:
    kwargs = {}
else:
    import api.docs  # noqa

    kwargs = dict(docs_url=None, redoc_url=None, openapi_url=None)
app = FastAPI(title="demo project", lifespan=task, responses=responses, **kwargs)
custom_openapi(app)

admin = Admin(app, async_db, authentication_backend=authentication_backend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(data_api)
app.include_router(token_api)

ApiException.register(app)

admin.add_view(UserAdmin)


@app.exception_handler(RequestValidationError)
async def handle_params_error(requset: Request, exc):
    detail = "; ".join([get_exc_loc(x["loc"]) + ": " + x["msg"] for x in exc.errors()])
    return JSONResponse(ERROR(detail).model_dump(), status_code=400)


@app.exception_handler(SQLAlchemyError)
async def handle_orm_error(request: Request, exc):
    return JSONResponse(ERROR(". ".join(exc.args)).model_dump(), status_code=500)


def get_exc_loc(info: tuple) -> str:
    if len(info) > 1:
        return info[1]
    else:
        return info[0]


@app.get("/time")
async def simpledemo() -> int:
    return int(time.time())


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=2,
        log_level=logging.INFO,
    )
