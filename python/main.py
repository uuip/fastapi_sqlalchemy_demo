import contextlib
import logging
import os
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from response import ERROR
from response.exceptions import ApiException
from routers.api import data_api
from routers.auth import token


@contextlib.asynccontextmanager
async def task(app):
    print("Run at startup!")
    yield
    print("Run on shutdown!")


app = FastAPI(title="demo project", lifespan=task)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(data_api)
app.include_router(token)

ApiException.register(app)


@app.exception_handler(RequestValidationError)
async def handle_params_error(requset: Request, exc):
    detail = "; ".join([get_exc_loc(x["loc"]) + ": " + x["msg"] for x in exc.errors()])
    return JSONResponse(ERROR(detail).model_dump())


@app.exception_handler(SQLAlchemyError)
async def handle_orm_error(request: Request, exc):
    return JSONResponse(ERROR(". ".join(exc.args)).model_dump())


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
        workers=os.cpu_count(),
        log_level=logging.INFO,
    )
