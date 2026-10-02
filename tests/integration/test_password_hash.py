from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.requests import Request

from app.admin.views import UserAdmin
from app.core.password import verify_password
from app.models import User
from app.services import account as account_service


async def test_create_account_stores_single_hash_verifiable_by_plain_password(db_session):
    # select(User.password) bypasses the identity map and returns the stored value.
    await account_service.create_account(db_session, username="hash-user", password="plain-pw", energy=10)

    stored_hash = await db_session.scalar(select(User.password).where(User.username == "hash-user"))

    assert stored_hash is not None
    assert stored_hash != "plain-pw"
    assert verify_password("plain-pw", stored_hash)


async def test_update_account_password_replaces_hash_correctly(db_session):
    created = await account_service.create_account(db_session, username="rehash-user", password="old-pw", energy=10)

    await account_service.update_account(db_session, account_id=created.id, fields={"password": "new-pw"})

    stored_hash = await db_session.scalar(select(User.password).where(User.id == created.id))

    assert verify_password("new-pw", stored_hash)
    assert not verify_password("old-pw", stored_hash)


async def test_admin_preserves_and_replaces_password_hashes(db_session, async_engine):
    admin = Admin(FastAPI(), async_engine)
    admin.add_view(UserAdmin)
    view = admin._views[0]
    view.session_maker = async_sessionmaker(
        bind=db_session.bind, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    request = Request({"type": "http", "method": "POST", "path": "/admin/user/create", "session": {}})

    created = await view.insert_model(request, {"username": "admin-created", "password": "old-pw", "energy": 10})
    original_hash = await db_session.scalar(select(User.password).where(User.id == created.id))
    assert verify_password("old-pw", original_hash)

    await view.update_model(request, str(created.id), {"password": original_hash, "energy": 20})
    unchanged_hash = await db_session.scalar(select(User.password).where(User.id == created.id))
    assert unchanged_hash == original_hash
    assert verify_password("old-pw", unchanged_hash)

    await view.update_model(request, str(created.id), {"password": "new-pw", "energy": 30})
    updated_hash = await db_session.scalar(select(User.password).where(User.id == created.id))
    assert verify_password("new-pw", updated_hash)
    assert not verify_password("old-pw", updated_hash)
