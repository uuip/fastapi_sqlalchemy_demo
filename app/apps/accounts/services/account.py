from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.accounts.models import User
from app.common.deps.pagination import CursorPage, CursorPagination, OffsetPage, OffsetPagination
from app.common.exceptions import ApiException


async def list_accounts(s: AsyncSession, *, pagination: OffsetPagination) -> OffsetPage[User]:
    qs = select(User).order_by(User.id)
    return await OffsetPage.create(s, qs, pagination)


async def query_accounts(
    s: AsyncSession,
    *,
    energy: int,
    pagination: CursorPagination,
) -> CursorPage[User]:
    if energy == 0:
        raise ApiException("demo error")
    qs = select(User).where(User.energy >= energy).order_by(User.id)
    return await CursorPage.create(s, qs, pagination, cursor_column=User.id)


async def read_account(s: AsyncSession, *, account_id: int) -> User | None:
    return await s.scalar(select(User).where(User.id == account_id))


async def create_account(
    s: AsyncSession,
    *,
    username: str,
    password: str,
    energy: int,
) -> User:
    account = User(username=username, password=password, energy=energy)
    s.add(account)
    await s.flush()
    return account


async def update_account(
    s: AsyncSession,
    *,
    account_id: int,
    fields: dict[str, Any],
) -> User | None:
    account = await read_account(s, account_id=account_id)
    if account is None:
        return None
    for name, value in fields.items():
        setattr(account, name, value)
    await s.flush()
    return account


async def delete_account(s: AsyncSession, *, account_id: int) -> bool:
    account = await read_account(s, account_id=account_id)
    if account is None:
        return False
    await s.delete(account)
    await s.flush()
    return True


async def create_random_account(s: AsyncSession) -> dict[str, int]:
    account = await create_account(s, username=f"demo-{uuid4().hex}", password="password", energy=333)
    return {"id": account.id}
