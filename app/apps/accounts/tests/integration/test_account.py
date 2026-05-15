from sqlalchemy import func, select

from app.apps.accounts.models import User
from app.apps.accounts.tests.helpers import create_user, login


async def test_add_account(client, db_session):
    rsp = await client.post("/account/add")
    assert rsp.status_code == 200
    data = rsp.json()
    assert "id" in data["data"]
    user = await db_session.scalar(select(User).where(User.id == data["data"]["id"]))
    assert user is not None
    assert user.username.startswith("demo-")
    assert user.energy == 333


async def test_get_account_returns_serialized_account(client, db_session):
    user = await create_user(db_session, username="detail-user", energy=123)

    rsp = await client.get(f"/account/{user.id}")

    assert rsp.status_code == 200
    body = rsp.json()
    assert body["code"] == 200
    assert body["msg"] == "success"
    assert body["data"]["id"] == user.id
    assert body["data"]["username"] == "detail-user"
    assert body["data"]["energy"] == 123
    assert "password" not in body["data"]
    assert body["data"]["someattr"] >= 2024


async def test_get_account_returns_404_for_missing_account(client):
    rsp = await client.get("/account/999999")

    assert rsp.status_code == 404
    assert rsp.json() == {"code": 404, "msg": "Account not found", "data": None}


async def test_query_accounts_filters_by_energy_and_cursor_paginates(client, db_session):
    await create_user(db_session, username="too-low", energy=100)
    first = await create_user(db_session, username="first-match", energy=250)
    second = await create_user(db_session, username="second-match", energy=300)
    third = await create_user(db_session, username="third-match", energy=350)

    first_page = await client.get("/account/q", params={"energy": 200, "size": 2})

    assert first_page.status_code == 200
    first_body = first_page.json()
    assert first_body["size"] == 2
    assert first_body["has_more"] is True
    assert first_body["next_cursor"] == second.id
    assert [item["id"] for item in first_body["data"]] == [first.id, second.id]

    second_page = await client.get(
        "/account/q",
        params={"energy": 200, "size": 2, "cursor": first_body["next_cursor"]},
    )

    assert second_page.status_code == 200
    second_body = second_page.json()
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None
    assert [item["id"] for item in second_body["data"]] == [third.id]


async def test_query_accounts_returns_demo_error_for_zero_energy(client):
    rsp = await client.get("/account/q", params={"energy": 0})

    assert rsp.status_code == 400
    assert rsp.json()["msg"] == "demo error"


async def test_query_accounts_rejects_negative_energy(client):
    rsp = await client.get("/account/q", params={"energy": -1})

    assert rsp.status_code == 422
    body = rsp.json()
    assert body["code"] == 422
    assert body["msg"] == "Request validation error"
    assert body["data"][0]["loc"] == ["query", "energy"]


async def test_update_account_requires_bearer_token(client, db_session):
    target = await create_user(db_session, username="target", energy=50)

    rsp = await client.post("/account/update", json={"id": target.id, "energy": 80})

    assert rsp.status_code == 401
    assert rsp.json() == {"code": 401, "msg": "Not authenticated", "data": None}


async def test_update_account_rejects_invalid_bearer_token(client, db_session):
    target = await create_user(db_session, username="target", energy=50)

    rsp = await client.post(
        "/account/update",
        json={"id": target.id, "energy": 80},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert rsp.status_code == 401
    assert rsp.json() == {"code": 401, "msg": "Could not validate credentials", "data": None}


async def test_update_account_changes_energy_when_authenticated(client, db_session):
    operator = await create_user(db_session, username="operator", energy=10)
    target = await create_user(db_session, username="target", energy=50)
    token = await login(client, username=operator.username)

    rsp = await client.post(
        "/account/update",
        json={"id": target.id, "energy": 80},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert rsp.status_code == 200
    body = rsp.json()
    assert body["data"] == {"id": target.id, "operator": "operator"}
    updated_target = await db_session.scalar(select(User).where(User.id == target.id))
    assert updated_target.energy == 80


async def test_update_account_returns_404_when_authenticated_account_is_missing(client, db_session):
    operator = await create_user(db_session, username="operator", energy=10)
    token = await login(client, username=operator.username)

    rsp = await client.post(
        "/account/update",
        json={"id": 999999, "energy": 80},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert rsp.status_code == 404
    assert rsp.json() == {"code": 404, "msg": "Account not found", "data": None}


async def test_no_leftover_data(db_session):
    st = select(func.count("*")).select_from(User)
    rst = await db_session.scalar(st)
    assert rst == 0
