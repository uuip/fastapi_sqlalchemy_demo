from tests.integration.helpers import create_user


async def test_login_returns_bearer_token(client, db_session):
    await create_user(db_session, username="login-user", energy=10)

    rsp = await client.post("/token", json={"username": "login-user", "password": "password"})

    assert rsp.status_code == 200
    body = rsp.json()
    assert body["code"] == 200
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["access_token"]


async def test_login_rejects_wrong_password(client, db_session):
    await create_user(db_session, username="login-user", energy=10)

    rsp = await client.post("/token", json={"username": "login-user", "password": "wrong"})

    assert rsp.status_code == 401
    assert rsp.json() == {"code": 401, "msg": "Incorrect username or password", "data": None}
    assert rsp.headers["www-authenticate"] == "Bearer"


async def test_login_rejects_missing_user(client):
    rsp = await client.post("/token", json={"username": "missing-user", "password": "password"})

    assert rsp.status_code == 401
    assert rsp.json() == {"code": 401, "msg": "Incorrect username or password", "data": None}
