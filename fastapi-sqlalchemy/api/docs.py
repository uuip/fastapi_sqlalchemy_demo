"""
定义app时docs_url=None, redoc_url=None, openapi_url=None;
重写实现添加身份认证
"""

from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from deps import UserDep
from main import app


@app.get("/docs", include_in_schema=False)
async def get_swagger_documentation(user: UserDep):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="docs")


@app.get("/redoc", include_in_schema=False)
async def get_redoc_documentation(user: UserDep):
    return get_redoc_html(openapi_url="/openapi.json", title="docs")


@app.get("/openapi.json", include_in_schema=False)
async def openapi(user: UserDep):
    return get_openapi(title=app.title, version=app.version, routes=app.routes)
