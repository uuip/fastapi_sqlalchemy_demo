import logging

from app.apps.accounts.tests.helpers import create_user
from tests.integration.helpers import capture_log_messages


async def test_setup_logging_forwards_stdlib_logs_after_app_startup(client):
    with capture_log_messages(message_prefix="integration stdlib log") as messages:
        stdlib_logger = logging.getLogger("integration.setup_logging")
        stdlib_logger.setLevel(logging.INFO)
        stdlib_logger.info("integration stdlib log")

    assert messages == ["integration stdlib log\n"]


async def test_log_request_records_successful_business_query(client, db_session):
    await create_user(db_session, username="below-threshold", energy=100)
    matched = await create_user(db_session, username="matched", energy=200)

    with capture_log_messages(message_prefix="GET /account/q query:") as messages:
        response = await client.get("/account/q", params={"energy": 150, "size": 1})

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == matched.id
    assert messages == ["GET /account/q query: {'energy': '150', 'size': '1'}\n"]


async def test_log_request_records_business_error_query_before_exception_handler(client):
    with capture_log_messages(message_prefix="GET /account/q query:") as messages:
        response = await client.get("/account/q", params={"energy": 0})

    assert response.status_code == 400
    assert response.json()["msg"] == "demo error"
    assert messages == ["GET /account/q query: {'energy': '0'}\n"]


async def test_log_request_records_json_body_for_existing_endpoint(client):
    with capture_log_messages(message_prefix="POST /example/json-body body:") as messages:
        response = await client.post(
            "/example/json-body",
            json={"item": {"name": "book", "description": "demo"}, "item2": 5},
        )

    assert response.status_code == 200
    assert response.json() == [{"name": "book", "description": "demo"}, 5]
    assert messages == ["POST /example/json-body body: {'item': {'name': 'book', 'description': 'demo'}, 'item2': 5}\n"]
