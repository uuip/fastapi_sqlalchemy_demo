from tests.integration.helpers import create_user


async def test_cursor_pagination_uses_default_size_and_reports_no_more(client, db_session):
    first = await create_user(db_session, username="first", energy=100)
    second = await create_user(db_session, username="second", energy=100)

    response = await client.get("/account/q", params={"energy": 100})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["size"] == 10
    assert body["has_more"] is False
    assert body["next_cursor"] is None
    assert [item["id"] for item in body["data"]] == [first.id, second.id]


async def test_cursor_pagination_filters_after_cursor_and_reports_next_cursor(client, db_session):
    first = await create_user(db_session, username="first", energy=100)
    second = await create_user(db_session, username="second", energy=100)
    third = await create_user(db_session, username="third", energy=100)

    response = await client.get("/account/q", params={"energy": 100, "cursor": first.id, "size": 1})

    assert response.status_code == 200
    body = response.json()
    assert body["size"] == 1
    assert body["has_more"] is True
    assert body["next_cursor"] == second.id
    assert [item["id"] for item in body["data"]] == [second.id]
    assert third.id > second.id


async def test_cursor_pagination_rejects_zero_size(client):
    response = await client.get("/account/q", params={"energy": 100, "size": 0})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 422
    assert body["msg"] == "Request validation error"
    assert body["data"][0]["loc"] == ["query", "size"]


async def test_cursor_pagination_rejects_non_integer_cursor(client):
    response = await client.get("/account/q", params={"energy": 100, "cursor": "abc"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == 422
    assert body["msg"] == "Request validation error"
    assert body["data"][0]["loc"] == ["query", "cursor"]
