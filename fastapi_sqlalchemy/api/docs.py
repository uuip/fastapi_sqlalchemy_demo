"""
定义app时docs_url=None, redoc_url=None, openapi_url=None;
重写实现添加身份认证
"""

from fastapi import APIRouter, Request
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from fastapi_sqlalchemy.deps import UserDep

docs_api = APIRouter()


@docs_api.get("/docs", include_in_schema=False)
async def get_swagger_documentation(user: UserDep):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")


@docs_api.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(user: UserDep):
    return get_redoc_html(openapi_url="/openapi.json", title="redoc")


@docs_api.get("/openapi.json", include_in_schema=False)
async def openapi(user: UserDep, request: Request):
    return get_openapi(title=request.app.title, version=request.app.version, routes=request.app.routes)
