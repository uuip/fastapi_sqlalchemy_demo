from typing import Annotated

from fastapi import Query, APIRouter
from sqlalchemy import select, update, func
from sqlalchemy.dialects.postgresql import insert

from fastapi_sqlalchemy.deps import SessionDep, CursorPage, CursorPageDep, UserDep
from fastapi_sqlalchemy.model import User
from fastapi_sqlalchemy.exceptions import ApiException
from fastapi_sqlalchemy.response import Rsp
from fastapi_sqlalchemy.schema import AccountSchema, Item

data_api = APIRouter(prefix="/account", dependencies=[], tags=["管理账户"])


@data_api.get("/q", response_model=CursorPage[AccountSchema], summary="条件查询（游标分页）")
async def query_accounts(energy: Annotated[int, Query(ge=0)], s: SessionDep, pagination: CursorPageDep):
    if energy == 0:
        raise ApiException("demo error")
    qs = select(User).where(User.balance >= energy).order_by(User.id)
    return await CursorPage.create(s, qs, pagination, cursor_column=User.id)


@data_api.get("/{id}", response_model=Rsp[AccountSchema], response_model_by_alias=False, summary="查询单个账户")
async def get_account(id: int, s: SessionDep):
    qs = select(User).where(User.id == id)
    return Rsp(await s.scalar(qs))


@data_api.post("/update", summary="更新单个")
async def update_account(item: Item, s: SessionDep, user: UserDep):
    qs = update(User).where(User.id == item.id).values(balance=item.energy)
    await s.execute(qs)
    user.updated_at = func.current_timestamp()
    await s.commit()
    return Rsp({"id": item.id, "operator": user.username})


@data_api.post("/add")
async def add_account(s: SessionDep):
    qs = insert(User).values(balance=333).returning(User)
    result = await s.scalar(qs)
    await s.commit()
    return Rsp({"id": result.id})
