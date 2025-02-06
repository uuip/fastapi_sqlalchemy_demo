from typing import Annotated

from fastapi import Query, APIRouter
from sqlalchemy import select, update, func

from deps import SessionDep, Page, PageDep, user_dep, UserDep
from model import Trees
from response import OK, Rsp, ApiException
from schema import TreeSchema, Item

data_api = APIRouter(prefix="/tree", dependencies=[user_dep], tags=["管理树木实体"])


@data_api.get("/q", response_model=Page[TreeSchema], summary="条件查询树木")
async def query_trees(energy: Annotated[int, Query(ge=0)], s: SessionDep, pagination: PageDep):
    if energy == 0:
        raise ApiException("demo error")
    qs = select(Trees).where(Trees.energy >= energy).order_by("id")
    return await Page.create(s, qs, pagination)


@data_api.get("/{id}", response_model=Rsp[TreeSchema], response_model_by_alias=False, summary="查询单个树木")
async def query_tree(id: int, s: SessionDep):
    qs = select(Trees).where(Trees.id == id)
    return OK(await s.scalar(qs))


@data_api.post("/update", summary="更新单个树木信息")
async def update_tree(item: Item, s: SessionDep, user: UserDep):
    qs = update(Trees).where(Trees.id == item.id).values(energy=item.energy)
    await s.execute(qs)
    user.updated_at = func.current_timestamp()
    await s.commit()
    return OK({"id": item.id, "operator": user.username})

    # return OK(obj)
    # return JSONResponse(status_code=status.HTTP_201_CREATED, content=item)
