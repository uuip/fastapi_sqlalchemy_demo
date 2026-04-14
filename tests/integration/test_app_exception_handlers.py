import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.services import account as account_service
from tests.integration.helpers import capture_error_records


def _iter_frames(traceback):
    while traceback is not None:
        yield traceback.tb_frame.f_code.co_filename, traceback.tb_frame.f_code.co_name
        traceback = traceback.tb_next


async def test_api_exception_handler_returns_business_error_from_existing_endpoint(client):
    response = await client.get("/account/q", params={"energy": 0})

    assert response.status_code == 400
    assert response.json()["code"] == 400
    assert response.json()["msg"] == "demo error"


async def test_validation_exception_handler_returns_422_for_invalid_query(client):
    response = await client.get("/account/q", params={"energy": -1})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 422
    assert body["msg"] == "Request validation error"
    assert body["data"][0]["loc"] == ["query", "energy"]


async def test_http_exception_handler_returns_uniform_error_response(client):
    response = await client.get("/users/999999")

    assert response.status_code == 404
    assert response.json() == {"code": 404, "msg": "User not found", "data": None}


async def test_not_found_route_returns_uniform_error_response_and_preserves_cors(client):
    response = await client.get("/not-existing-path", headers={"Origin": "http://example.com"})

    assert response.status_code == 404
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.json() == {"code": 404, "msg": "Not Found", "data": None}


async def test_sqlalchemy_exception_handler_returns_500_and_logs_project_trace(client, monkeypatch: pytest.MonkeyPatch):
    async def broken_add_account(_session):
        raise SQLAlchemyError("integration database failure")

    monkeypatch.setattr(account_service, "create_random_account", broken_add_account)

    with capture_error_records() as records:
        response = await client.post("/account/add")

    assert response.status_code == 500
    assert response.json()["msg"] == "Database operation failed"
    db_errors = [record for record in records if record["message"].startswith("Database operation error:")]
    assert len(db_errors) == 1
    assert db_errors[0]["exception"] is not None
    assert db_errors[0]["exception"].value.args == ("integration database failure",)
    assert db_errors[0]["exception"].traceback is not None
    frames = list(_iter_frames(db_errors[0]["exception"].traceback))
    assert any(fn.endswith("app/api/account.py") and name == "add_account" for fn, name in frames)


async def test_unhandled_exception_middleware_returns_500_logs_project_trace_and_preserves_cors(
    client,
    monkeypatch: pytest.MonkeyPatch,
):
    async def broken_add_account(_session):
        raise RuntimeError("integration unexpected failure")

    monkeypatch.setattr(account_service, "create_random_account", broken_add_account)

    with capture_error_records() as records:
        response = await client.post("/account/add", headers={"Origin": "http://example.com"})

    assert response.status_code == 500
    assert response.json()["msg"] == "Internal server error"
    assert response.headers["access-control-allow-origin"] == "*"
    unhandled_errors = [record for record in records if record["message"] == "Unhandled error: POST /account/add"]
    assert len(unhandled_errors) == 1
    assert unhandled_errors[0]["exception"] is not None
    assert unhandled_errors[0]["exception"].value.args == ("integration unexpected failure",)
    assert unhandled_errors[0]["exception"].traceback is not None
    frames = list(_iter_frames(unhandled_errors[0]["exception"].traceback))
    assert any(fn.endswith("app/api/account.py") and name == "add_account" for fn, name in frames)
