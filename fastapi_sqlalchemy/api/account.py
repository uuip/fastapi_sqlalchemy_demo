from typing import Annotated

from fastapi import Query, APIRouter
from sqlalchemy import select, update, func
from sqlalchemy.dialects.postgresql import insert

from fastapi_sqlalchemy.deps import SessionDep, Page, PageDep, UserDep
from fastapi_sqlalchemy.model import Account
from fastapi_sqlalchemy.response import Rsp, ApiException
from fastapi_sqlalchemy.schema import AccountSchema, Item

data_api = APIRouter(prefix="/account", dependencies=[], tags=["管理账户"])


@data_api.get("/q", response_model=Page[AccountSchema], summary="条件查询")
async def query_accounts(energy: Annotated[int, Query(ge=0)], s: SessionDep, pagination: PageDep):
    if energy == 0:
        raise ApiException("demo error")
    qs = select(Account).where(Account.balance >= energy).order_by("id")
    return await Page.create(s, qs, pagination)


@data_api.get("/{id}", response_model=Rsp[AccountSchema], response_model_by_alias=False, summary="查询单个账户")
async def get_account(id: int, s: SessionDep):
    qs = select(Account).where(Account.id == id)
    return Rsp(await s.scalar(qs))


@data_api.post("/update", summary="更新单个")
async def update_account(item: Item, s: SessionDep, user: UserDep):
    qs = update(Account).where(Account.id == item.id).values(balance=item.energy)
    await s.execute(qs)
    user.updated_at = func.current_timestamp()
    await s.commit()
    return Rsp({"id": item.id, "operator": user.username})


@data_api.post("/add")
async def add_account(s: SessionDep):
    qs = insert(Account).values(balance=333).returning(Account)
    result = await s.scalar(qs)
    await s.commit()
    return Rsp({"id": result.id})
