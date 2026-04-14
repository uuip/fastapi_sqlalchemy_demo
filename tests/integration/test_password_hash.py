from sqlalchemy import select

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
