import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.core.exception_handlers import install_exception_handlers
from app.core.exceptions import ApiException
from app.core.middleware import CatchAllExceptionMiddleware


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
    assert response.json() == {"code": 404, "msg": "resource not found", "data": None}


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
    assert len(body["data"]) == 1
    assert body["data"][0]["type"] == "missing"
    assert body["data"][0]["loc"] == ["body", "quantity"]
    assert body["data"][0]["input"] == {"name": "test"}


async def test_request_validation_error_is_logged_as_warning():
    from loguru import logger

    app = _make_app()
    records = []
    sink = logger.add(lambda message: records.append(message.record), format="{message}")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/validation-error", json={"name": "test"})
    finally:
        logger.remove(sink)

    assert response.status_code == 422
    validation_records = [record for record in records if record["message"].startswith("Request validation error:")]
    assert len(validation_records) == 1
    assert validation_records[0]["level"].name == "WARNING"


async def test_http_exception_handler_returns_error_response():
    app = _make_app()

    @app.get("/http-error")
    async def http_error():
        raise HTTPException(status_code=404, detail="resource not found")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/http-error")

    assert response.status_code == 404
    assert response.json() == {"code": 404, "msg": "resource not found", "data": None}


@pytest.mark.parametrize(
    "exc",
    [
        pytest.param(
            HTTPException(401, "Could not validate credentials", headers={"WWW-Authenticate": "Bearer"}), id="http"
        ),
        pytest.param(
            ApiException("Could not validate credentials", status_code=401, headers={"WWW-Authenticate": "Bearer"}),
            id="business",
        ),
    ],
)
async def test_http_exception_handler_preserves_headers(exc):
    app = _make_app()

    @app.get("/http-error-with-headers")
    async def http_error_with_headers():
        raise exc

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
    assert response.json() == {"code": 500, "msg": "Database operation failed", "data": None}


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


async def test_validation_errors_do_not_expose_passwords_in_logs_or_responses():
    from loguru import logger

    from app.schemas.auth import LoginRequest

    app = FastAPI()
    install_exception_handlers(app)

    @app.post("/login-validation")
    async def login_validation(body: LoginRequest):
        return {"username": body.username}

    password = "VALIDATION_SECRET_" + "x" * 128
    messages = []
    sink = logger.add(lambda message: messages.append(str(message)), format="{message}")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/login-validation", json={"username": "alice", "password": password})
    finally:
        logger.remove(sink)

    assert response.status_code == 422
    assert password not in response.text
    assert all(password not in message for message in messages)
    issue = next(item for item in response.json()["data"] if item["loc"] == ["body", "password"])
    assert issue["type"] == "string_too_long"
    assert issue["input"] == "***"
