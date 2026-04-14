import pytest
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient


def _make_app_catchall_before_cors() -> FastAPI:
    """正确做法：catch-all middleware 加在 CORSMiddleware 之前（内层）。

    add_middleware 每次插入到 user_middleware[0]（外层），所以后加的 CORS
    在外层，先加的 catch-all 在内层。catch-all 捕获异常后返回的响应会
    向外流经 CORSMiddleware，CORS 头被正确添加。
    """
    app = FastAPI()

    # 先加 catch-all → 位于 user_middleware 尾部（内层）
    @app.middleware("http")
    async def catch_all(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            return JSONResponse({"error": "internal error"}, status_code=500)

    # 后加 CORS → 位于 user_middleware 头部（外层），包裹 catch-all
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/crash")
    async def crash():
        raise RuntimeError("boom")

    return app


def _make_app_catchall_after_cors() -> FastAPI:
    """错误做法：catch-all middleware 加在 CORSMiddleware 之后（外层）。

    catch-all 在 CORS 外层，捕获异常后的响应直接返回给 ServerErrorMiddleware，
    绕过了 CORSMiddleware，CORS 头丢失。
    """
    app = FastAPI()

    # 先加 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 后加 catch-all → 位于 CORS 外层
    @app.middleware("http")
    async def catch_all(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception:
            return JSONResponse({"error": "internal error"}, status_code=500)

    @app.get("/crash")
    async def crash():
        raise RuntimeError("boom")

    return app


def _make_app_exception_handler() -> FastAPI:
    """错误做法：用 @app.exception_handler(Exception)。

    Starlette 把 Exception handler 挂到 ServerErrorMiddleware（最外层），
    它发送响应后还会重新抛出异常，导致 httpx 收到的是异常而非响应。
    """
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def catch_all(request: Request, exc: Exception):
        return JSONResponse({"error": "internal error"}, status_code=500)

    @app.get("/crash")
    async def crash():
        raise RuntimeError("boom")

    return app


async def test_catchall_before_cors_preserves_headers():
    """catch-all 在 CORS 内层 → 500 响应携带 CORS 头。"""
    app = _make_app_catchall_before_cors()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/crash", headers={"Origin": "http://example.com"})

    print("\n[正确做法] catch-all 在 CORS 内层")
    print(f"  status_code: {response.status_code}")
    print(f"  headers: {dict(response.headers)}")
    print(f"  access-control-allow-origin: {response.headers.get('access-control-allow-origin', '<缺失>')}")

    assert response.status_code == 500
    assert "access-control-allow-origin" in response.headers


async def test_catchall_after_cors_loses_headers():
    """catch-all 在 CORS 外层 → 500 响应丢失 CORS 头。"""
    app = _make_app_catchall_after_cors()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/crash", headers={"Origin": "http://example.com"})

    print("\n[错误做法] catch-all 在 CORS 外层")
    print(f"  status_code: {response.status_code}")
    print(f"  headers: {dict(response.headers)}")
    print(f"  access-control-allow-origin: {response.headers.get('access-control-allow-origin', '<缺失>')}")

    assert response.status_code == 500
    assert "access-control-allow-origin" not in response.headers


async def test_exception_handler_propagates_exception():
    """@app.exception_handler(Exception) 挂在 ServerErrorMiddleware（最外层），
    它发送响应后总是重新抛出异常，httpx 收到异常而非响应。"""
    app = _make_app_exception_handler()
    print("\n[错误做法] @app.exception_handler(Exception)")
    print("  ServerErrorMiddleware 处理后总是重新抛出异常，httpx 收到 RuntimeError 而非响应")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with pytest.raises(RuntimeError):
            await client.get("/crash", headers={"Origin": "http://example.com"})
