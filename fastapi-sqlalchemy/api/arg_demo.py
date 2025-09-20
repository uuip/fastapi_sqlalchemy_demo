from typing import Annotated

from fastapi import Query, Path, Body, APIRouter
from pydantic import BaseModel, Field

arg_api = APIRouter(prefix="/arg")


class Item(BaseModel):
    name: str
    description: str | None = None


class Item2(BaseModel):
    price: float
    tax: float | None = None


class Item3(BaseModel):
    address: str


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)


@arg_api.get("/path/{uid}/{uid2}/{uid3}")
async def arg_path(
    uid: int,
    uid2: Annotated[int, Path(title="The ID of the item to get")],
    uid3: int = Path(title="The ID of the item to get"),
):
    return uid, uid2, uid3


@arg_api.get("/query/")
async def arg_query(
    q: str,
    q2: Annotated[str | None, Query(max_length=50)] = None,
    q3: str | None = Query(default=None, max_length=50),
):
    return q, q2, q3


# 所有请求参数都转换为query，不能再添加单独的请求参数定义
@arg_api.get("/query_model/")
async def arg_query_model(
    query: Annotated[FilterParams, Query()],
    # query: FilterParams = Query(),
):
    return query


# {
#     "name": "string",
#     "description": "string",
# }
@arg_api.post("/body/")
async def arg_body(item: Item):
    return item


# {
#   "item": {
#     "name": "string",
#     "description": "string"
#   },
#   "item2": {
#     "price": 0,
#     "tax": 0
#   },
#   "item3": {
#     "address": "string"
#   }
# }
@arg_api.post("/body_multi/")
async def arg_body_multi(
    item: Item,
    item2: Annotated[Item2, Body()],
    item3: Item3 = Body(),
):
    return item, item2, item3


# {
#   "item":3,
#   "item2": 4
# }
# return [3, 4]
@arg_api.post("/body_2single/")
async def arg_body_single(item: Annotated[int, Body()], item2: int = Body()):
    return item, item2


# 如果没有embed=True，由于类型标注为int，传入json只能是数字 33
# 有embed=True，传入 {"data":33}后，data=33
@arg_api.post("/body_1single/")
async def arg_body_single(data: Annotated[int, Body(embed=True)]):
    return data
