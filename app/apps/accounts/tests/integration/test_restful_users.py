import pytest
from sqlalchemy import select

from app.apps.accounts.models import User
from app.apps.accounts.services import account as account_service


async def test_users_resource_supports_standard_restful_crud(client, db_session):
    create_rsp = await client.post("/users", json={"username": "rest-user", "password": "secret", "energy": 10})

    assert create_rsp.status_code == 201
    created = create_rsp.json()
    assert created["id"] > 0
    assert created["username"] == "rest-user"
    assert created["energy"] == 10
    assert "password" not in created

    list_rsp = await client.get("/users", params={"page": 1, "size": 10})

    assert list_rsp.status_code == 200
    listed = list_rsp.json()
    assert listed["page"] == 1
    assert listed["size"] == 10
    assert listed["total"] >= 1
    assert created in listed["data"]

    detail_rsp = await client.get(f"/users/{created['id']}")

    assert detail_rsp.status_code == 200
    assert detail_rsp.json() == created

    replace_rsp = await client.put(
        f"/users/{created['id']}",
        json={"username": "rest-user-replaced", "password": "new-secret", "energy": 20},
    )

    assert replace_rsp.status_code == 200
    replaced = replace_rsp.json()
    assert replaced == {"id": created["id"], "username": "rest-user-replaced", "energy": 20}

    patch_rsp = await client.patch(f"/users/{created['id']}", json={"energy": 30})

    assert patch_rsp.status_code == 200
    patched = patch_rsp.json()
    assert patched == {"id": created["id"], "username": "rest-user-replaced", "energy": 30}

    stored = await db_session.scalar(select(User).where(User.id == created["id"]))
    await db_session.refresh(stored, attribute_names=["password"])
    assert stored.check_password("new-secret")

    delete_rsp = await client.delete(f"/users/{created['id']}")

    assert delete_rsp.status_code == 204
    assert delete_rsp.content == b""
    deleted = await db_session.scalar(select(User).where(User.id == created["id"]))
    assert deleted is None


async def test_patch_user_rejects_explicit_null_for_energy(client, db_session):
    target = await account_service.create_account(
        db_session, username="patch-null-energy", password="secret", energy=42
    )
    await db_session.commit()

    rsp = await client.patch(f"/users/{target.id}", json={"energy": None})

    assert rsp.status_code == 422
    body = rsp.json()
    assert body["code"] == 422
    assert any(issue["loc"] == ["body", "energy"] for issue in body["data"])


async def test_patch_user_rejects_explicit_null_for_username(client, db_session):
    target = await account_service.create_account(
        db_session, username="patch-null-username", password="secret", energy=10
    )
    await db_session.commit()

    rsp = await client.patch(f"/users/{target.id}", json={"username": None})

    assert rsp.status_code == 422
    body = rsp.json()
    assert any(issue["loc"] == ["body", "username"] for issue in body["data"])


async def test_users_resource_returns_404_for_missing_user(client):
    rsp = await client.get("/users/999999")

    assert rsp.status_code == 404
    assert rsp.json() == {"code": 404, "msg": "User not found", "data": None}


async def test_create_user_delegates_to_account_service_create_entrypoint(client, monkeypatch: pytest.MonkeyPatch):
    calls = {}

    class CreatedUser:
        id = 123
        username = "delegated-user"
        energy = 42

    async def fake_create_account(session, *, username: str, password: str, energy: int):
        calls["session"] = session
        calls["username"] = username
        calls["password"] = password
        calls["energy"] = energy
        return CreatedUser()

    monkeypatch.setattr(account_service, "create_account", fake_create_account)

    rsp = await client.post("/users", json={"username": "delegated-user", "password": "secret", "energy": 42})

    assert rsp.status_code == 201
    assert rsp.json() == {"id": 123, "username": "delegated-user", "energy": 42}
    assert calls["username"] == "delegated-user"
    assert calls["password"] == "secret"
    assert calls["energy"] == 42
