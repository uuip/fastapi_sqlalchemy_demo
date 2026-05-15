import threading
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI, Request
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.common import logging as core_logging
from app.common.logging import log_request


class Payload(BaseModel):
    name: str


def make_app(
    messages: list[tuple[object, tuple[object, ...]]],
    monkeypatch: pytest.MonkeyPatch,
) -> FastAPI:
    app = FastAPI()

    def fake_info(message, *args, **kwargs):
        messages.append((message, args))

    monkeypatch.setattr(core_logging.logger, "info", fake_info)

    def marker() -> str:
        return "ok"

    @app.post("/bare")
    @log_request
    async def bare(payload: Payload):
        return {"name": payload.name}

    @log_request
    @app.post("/route-first-bare")
    async def route_first_bare(payload: Payload):
        return {"name": payload.name}

    @app.post("/factory")
    @log_request()
    async def factory(payload: Payload, marker_value: Annotated[str, Depends(marker)]):
        return {"name": payload.name, "marker": marker_value}

    @log_request()
    @app.post("/route-first-factory")
    async def route_first_factory(payload: Payload, marker_value: Annotated[str, Depends(marker)]):
        return {"name": payload.name, "marker": marker_value}

    @app.post("/plain")
    async def plain(payload: Payload):
        return {"name": payload.name}

    @app.get("/decorated-get")
    @log_request
    async def decorated_get():
        return {"ok": True}

    @app.post("/sync")
    @log_request
    def sync_endpoint(payload: Payload):
        return {"name": payload.name}

    @app.post("/sync-thread")
    @log_request
    def sync_thread_endpoint(payload: Payload):
        return {"same_thread": threading.get_ident() == app.state.main_thread_id}

    @app.post("/with-request")
    @log_request
    async def with_request(payload: Payload, request: Request):
        return {"name": payload.name, "method": request.method}

    @app.delete("/items/{item_id}")
    @log_request
    async def delete_item(item_id: int):
        return {"deleted": item_id}

    @app.post("/search")
    @log_request
    async def search(payload: Payload):
        return {"name": payload.name}

    return app


async def test_log_request_supports_bare_decorator(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/bare", json={"name": "Alice"})

    assert response.status_code == 200
    assert response.json() == {"name": "Alice"}
    assert messages == [("{} {} body: {}", ("POST", "/bare", {"name": "Alice"}))]


async def test_log_request_above_route_decorator_does_not_wrap_registered_endpoint(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/route-first-bare", json={"name": "Alice"})

    assert response.status_code == 200
    assert response.json() == {"name": "Alice"}
    assert messages == []


async def test_log_request_supports_factory_decorator_and_dependencies(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/factory", json={"name": "Bob"})

    assert response.status_code == 200
    assert response.json() == {"name": "Bob", "marker": "ok"}
    assert messages == [("{} {} body: {}", ("POST", "/factory", {"name": "Bob"}))]


async def test_log_request_factory_above_route_decorator_does_not_wrap_registered_endpoint(
    monkeypatch: pytest.MonkeyPatch,
):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/route-first-factory", json={"name": "Bob"})

    assert response.status_code == 200
    assert response.json() == {"name": "Bob", "marker": "ok"}
    assert messages == []


async def test_log_request_does_not_run_without_decorator(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/plain", json={"name": "Charlie"})

    assert response.status_code == 200
    assert response.json() == {"name": "Charlie"}
    assert messages == []


async def test_log_request_skips_get_without_query(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/decorated-get")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert messages == []


async def test_log_request_logs_get_query_params(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/decorated-get", params={"q": "hello", "page": "2"})

    assert response.status_code == 200
    assert messages == [("{} {} query: {}", ("GET", "/decorated-get", {"q": "hello", "page": "2"}))]


async def test_log_request_supports_sync_routes(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/sync", json={"name": "Dana"})

    assert response.status_code == 200
    assert response.json() == {"name": "Dana"}
    assert messages == [("{} {} body: {}", ("POST", "/sync", {"name": "Dana"}))]


async def test_log_request_keeps_sync_routes_in_threadpool(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)
    app.state.main_thread_id = threading.get_ident()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/sync-thread", json={"name": "Eve"})

    assert response.status_code == 200
    assert response.json() == {"same_thread": False}


async def test_log_request_reuses_explicit_request_param(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/with-request", json={"name": "Frank"})

    assert response.status_code == 200
    assert response.json() == {"name": "Frank", "method": "POST"}
    assert messages == [("{} {} body: {}", ("POST", "/with-request", {"name": "Frank"}))]


async def test_log_request_logs_delete_query_params(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete("/items/42", params={"force": "true"})

    assert response.status_code == 200
    assert response.json() == {"deleted": 42}
    assert messages == [("{} {} query: {}", ("DELETE", "/items/42", {"force": "true"}))]


async def test_log_request_skips_delete_without_query(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete("/items/7")

    assert response.status_code == 200
    assert messages == []


async def test_log_request_logs_post_query_and_body(monkeypatch: pytest.MonkeyPatch):
    messages: list[tuple[object, tuple[object, ...]]] = []
    app = make_app(messages, monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/search", params={"page": "2"}, json={"name": "Gina"})

    assert response.status_code == 200
    assert response.json() == {"name": "Gina"}
    assert messages == [
        ("{} {} query: {}", ("POST", "/search", {"page": "2"})),
        ("{} {} body: {}", ("POST", "/search", {"name": "Gina"})),
    ]
