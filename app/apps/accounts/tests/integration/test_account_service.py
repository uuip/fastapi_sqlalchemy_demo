from sqlalchemy import select

from app.apps.accounts.models import User
from app.apps.accounts.services import account as account_service


async def test_create_read_update_account_through_crud_entrypoints(db_session):
    created = await account_service.create_account(
        db_session,
        username="service-user",
        password="secret",
        energy=10,
    )

    assert created.id is not None
    assert created.username == "service-user"
    assert created.energy == 10

    read = await account_service.read_account(db_session, account_id=created.id)

    assert read == created

    replaced = await account_service.update_account(
        db_session,
        account_id=created.id,
        fields={"username": "service-user-replaced", "password": "new-secret", "energy": 20},
    )

    assert replaced == created
    assert replaced.username == "service-user-replaced"
    assert replaced.energy == 20
    # PassWord hashes only on persistence; refresh to read the stored hash.
    await db_session.refresh(replaced, attribute_names=["password"])
    assert replaced.check_password("new-secret")

    patched = await account_service.update_account(
        db_session,
        account_id=created.id,
        fields={"energy": 30},
    )

    assert patched == created
    assert patched.username == "service-user-replaced"
    assert patched.energy == 30

    stored = await db_session.scalar(select(User).where(User.id == created.id))
    assert stored == created


async def test_update_account_returns_none_when_updating_missing_account(db_session):
    result = await account_service.update_account(
        db_session,
        account_id=999999,
        fields={"energy": 30},
    )

    assert result is None


async def test_update_account_with_empty_fields_is_a_noop(db_session):
    created = await account_service.create_account(db_session, username="noop-user", password="secret", energy=10)

    result = await account_service.update_account(db_session, account_id=created.id, fields={})

    assert result == created
    assert result.username == "noop-user"
    assert result.energy == 10


async def test_create_account_flushes_without_owning_transaction(db_session, monkeypatch):
    calls = {"commit": 0}
    real_commit = db_session.commit

    async def count_commit():
        calls["commit"] += 1
        await real_commit()

    monkeypatch.setattr(db_session, "commit", count_commit)

    account = await account_service.create_account(
        db_session,
        username="deferred-user",
        password="secret",
        energy=10,
    )

    assert account.id is not None
    assert calls["commit"] == 0
