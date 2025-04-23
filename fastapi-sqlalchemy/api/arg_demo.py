from typing import Annotated, Literal

from fastapi import Query, Path, Body
from pydantic import BaseModel, Field

from main import app


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None


class FilterParams(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    order_by: Literal["created_at", "updated_at"] = "created_at"
    tags: list[str] = []


@app.get("/arg/{uid}/{item_id}/{item_id2}")
async def arg_path(
    uid: int,
    item_id: Annotated[int, Path(title="The ID of the item to get")],
    item_id2: int = Path(title="The ID of the item to get"),
) -> int:
    return uid, item_id, item_id2


@app.get("/arg/")
async def arg_query(
    q: str,
    q2: Annotated[str | None, Query(max_length=50)] = None,
    q3: str | None = Query(default=None, max_length=50),
) -> int:
    return q, q2, q3


@app.get("/arg/")
async def arg_query_model(
    filter_query: Annotated[FilterParams, Query()],
    filter_query2: FilterParams = Query(),
):
    return filter_query, filter_query2


@app.post("/arg/")
async def arg_body(
    item: Item,
    item2: Annotated[Item, Body()],
    item3: Item = Body(),
) -> int:
    return item, item2, item3


@app.post("/arg/")
async def arg_body_single(
    importance: Annotated[int, Body()],
    importance2: int = Body(),  # embed=True
) -> int:
    return importance, importance2
