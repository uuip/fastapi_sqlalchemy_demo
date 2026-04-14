"""Validate that all password-accepting endpoints reject overlong passwords."""

from app.schemas.auth import PASSWORD_MAX_LENGTH
from tests.integration.helpers import create_user

LONG_PASSWORD = "x" * (PASSWORD_MAX_LENGTH + 1)


async def test_login_rejects_overlong_password(client):
    rsp = await client.post("/token", json={"username": "any", "password": LONG_PASSWORD})

    assert rsp.status_code == 422
    body = rsp.json()
    assert body["code"] == 422
    assert any(issue["loc"] == ["body", "password"] for issue in body["data"])


async def test_create_user_rejects_overlong_password(client):
    rsp = await client.post(
        "/users",
        json={"username": "u", "password": LONG_PASSWORD, "energy": 1},
    )

    assert rsp.status_code == 422
    body = rsp.json()
    assert any(issue["loc"] == ["body", "password"] for issue in body["data"])


async def test_replace_user_rejects_overlong_password(client, db_session):
    target = await create_user(db_session, username="replace-target", energy=1)

    rsp = await client.put(
        f"/users/{target.id}",
        json={"username": "replace-target", "password": LONG_PASSWORD, "energy": 1},
    )

    assert rsp.status_code == 422
    body = rsp.json()
    assert any(issue["loc"] == ["body", "password"] for issue in body["data"])


async def test_patch_user_rejects_overlong_password(client, db_session):
    target = await create_user(db_session, username="patch-target", energy=1)

    rsp = await client.patch(f"/users/{target.id}", json={"password": LONG_PASSWORD})

    assert rsp.status_code == 422
    body = rsp.json()
    assert any(issue["loc"] == ["body", "password"] for issue in body["data"])
