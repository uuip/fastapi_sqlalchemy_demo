import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.common.exception_handlers import install_exception_handlers
from app.common.exceptions import ApiException
from app.common.middleware import CatchAllExceptionMiddleware


class Item(BaseModel):
    name: str
    quantity: int


def _make_app() -> FastAPI:
    app = FastAPI()
    install_exception_handlers(app)
    app.add_middleware(CatchAllExceptionMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api-error")
    async def api_error():
        raise ApiException("resource not found", status_code=404)

    @app.get("/api-error-default")
    async def api_error_default():
        raise ApiException("bad input")

    @app.post("/validation-error")
    async def validation_error(item: Item):
        return {"name": item.name}

    @app.get("/db-error")
    async def db_error():
        raise SQLAlchemyError("connection lost")

    @app.get("/unhandled-error")
    async def unhandled_error():
        raise RuntimeError("unexpected crash")

    return app


async def test_api_exception_handler():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api-error")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == 404
    assert body["msg"] == "resource not found"


async def test_api_exception_default_status_code():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api-error-default")

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 400
    assert body["msg"] == "bad input"


async def test_request_validation_error():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/validation-error", json={"name": "test"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 422
    assert body["msg"] == "Request validation error"
    assert body["data"] is not None
    assert len(body["data"]) > 0


async def test_http_exception_handler_returns_error_response():
    app = _make_app()

    @app.get("/http-error")
    async def http_error():
        raise HTTPException(status_code=404, detail="resource not found")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/http-error")

    assert response.status_code == 404
    assert response.json() == {"code": 404, "msg": "resource not found", "data": None}


async def test_http_exception_handler_preserves_headers():
    app = _make_app()

    @app.get("/http-error-with-headers")
    async def http_error_with_headers():
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/http-error-with-headers")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"code": 401, "msg": "Could not validate credentials", "data": None}


async def test_http_exception_handler_keeps_non_string_detail_as_data():
    app = _make_app()

    @app.get("/http-error-with-object-detail")
    async def http_error_with_object_detail():
        raise HTTPException(status_code=400, detail={"field": "username"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/http-error-with-object-detail")

    assert response.status_code == 400
    assert response.json() == {"code": 400, "msg": "Bad Request", "data": {"field": "username"}}


async def test_sqlalchemy_error():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/db-error")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == 500
    assert body["msg"] == "Database operation failed"


async def test_unhandled_exception_catch_all():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/unhandled-error")

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == 500
    assert body["msg"] == "Internal server error"


async def test_catch_all_middleware_preserves_cors_headers():
    app = _make_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/unhandled-error", headers={"Origin": "http://example.com"})

    assert response.status_code == 500
    assert "access-control-allow-origin" in response.headers


async def test_streaming_error_after_first_chunk_propagates():
    """After response headers are sent, the catch-all must re-raise rather
    than swallow — otherwise the ASGI response is never properly closed
    and downstream clients see protocol errors."""
    app = _make_app()

    async def stream_then_crash():
        yield b"first chunk\n"
        raise RuntimeError("mid-stream crash")

    @app.get("/stream-crash")
    async def stream_crash():
        return StreamingResponse(stream_then_crash(), media_type="text/plain")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        with pytest.raises(RuntimeError, match="mid-stream crash"):
            await client.get("/stream-crash")
