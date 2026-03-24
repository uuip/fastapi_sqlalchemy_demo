from typing import Annotated

from fastapi import (
    Query,
    Path,
    Body,
    Form,
    UploadFile,
    APIRouter,
    Depends,
    Request,
    )
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

arg_api = APIRouter(prefix="/arg")


class Item(BaseModel):
    name: str
    description: str | None = None


class Item2(BaseModel):
    price: float
    tax: float | None = None


class Pagination(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)


@arg_api.get("/path/{uid}/{uid2}/{uid3}")
async def arg_path(
    uid: int,
    uid2: Annotated[int, Path()],
    uid3: int = Path(),
):
    """
    GET http://127.0.0.1:8000/arg/path/1/2/3
    """
    return uid, uid2, uid3


@arg_api.get("/query/")
async def arg_query(
    q: str,
    q2: Annotated[str | None, Query(max_length=50)] = None,
    q3: str | None = Query(default=None, max_length=50),
):
    """
    GET http://127.0.0.1:8000/arg/query/?q=a&q2=b&q3=c
    """
    return q, q2, q3


@arg_api.get("/query_model/")
async def arg_query_model(
    query: Annotated[Pagination, Depends()],
    q4: Item = Depends(),
):
    return query, q4


# {
#   "item": {
#     "name": "string",
#     "description": "string"
#   },
#   "item2": 5
# }
@arg_api.post("/body/")
async def arg_body(
    item: Item,
    item2: Annotated[int, Body()],
):
    return item, item2


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


@arg_api.post("/upload/")
async def upload_files(
    files: list[UploadFile],
    template_ids: Annotated[list[int], Form()],
):
    """
    POST http://127.0.0.1:8000/arg/upload/
    Content-Type: multipart/form-data

    files: file1.pdf
    files: file2.pdf
    template_ids: 101
    template_ids: 102
    """
    return [
        {
            "filename": f.filename,
            "content_type": f.content_type,
            "template_id": tid,
        }
        for f, tid in zip(files, template_ids)
    ]


@arg_api.post("/body")
async def file(request: Request):
    body = await request.body()
    return jsonable_encoder(body)


@arg_api.post("/file")
async def file(request: Request):
    form = await request.form()
    # template_ids = form.getlist("template_ids")
    return {}
