from typing import Annotated

from fastapi import Query, APIRouter
from sqlalchemy import select, update, func

from dependencies import DBDep, Page, PageDep, user_dep, UserDep
from models import Trees
from response import OK, Rsp, ApiException, ErrRsp
from schemas import TreeSchema, Item

# 指定当http状态码==422时，返回ErrRsp模型；使docs正确渲染
responses = {400: {"model": ErrRsp}}
data_api = APIRouter(prefix="/tree", dependencies=[user_dep], tags=["管理树木实体"], responses=responses)


@data_api.get("/q", response_model=Page[TreeSchema], summary="条件查询树木")
async def query_trees(energy: Annotated[int, Query(ge=0)], s: DBDep, pagination: PageDep):
    if energy == 0:
        raise ApiException("demo error")
    qs = select(Trees).where(Trees.energy >= energy).order_by("id")
    return await Page.create(s, qs, pagination)


@data_api.get("/{id}", response_model=Rsp[TreeSchema], response_model_by_alias=False, summary="查询单个树木")
async def query_tree(id: int, s: DBDep):
    qs = select(Trees).where(Trees.id == id)
    return OK(await s.scalar(qs))


@data_api.post("/update", summary="更新单个树木信息")
async def update_tree(item: Item, s: DBDep, user: UserDep):
    print(id(s), type(s), update_tree)
    qs = update(Trees).where(Trees.id == item.id).values(energy=item.energy)
    await s.execute(qs)
    user.updated_at = func.current_timestamp()
    operator = user.username
    await s.commit()
    return OK({"id": item.id, "operator": operator})

    # return OK(obj)
    # return JSONResponse(status_code=status.HTTP_201_CREATED, content=item)
