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

example_api = APIRouter(prefix="/example", tags=["Parameter Examples"])


class Item(BaseModel):
    name: str
    description: str | None = None


class Item2(BaseModel):
    price: float
    tax: float | None = None


class Pagination(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)


@example_api.get("/path/{uid}/{uid2}/{uid3}")
async def demo_path_params(
    uid: int,
    uid2: Annotated[int, Path()],
    uid3: int = Path(),
):
    """
    GET http://127.0.0.1:8000/example/path/1/2/3
    """
    return uid, uid2, uid3


@example_api.get("/query/")
async def demo_query_params(
    q: str,
    q2: Annotated[str | None, Query(max_length=50)] = None,
    q3: str | None = Query(default=None, max_length=50),
):
    """
    GET http://127.0.0.1:8000/example/query/?q=a&q2=b&q3=c
    """
    return q, q2, q3


@example_api.get("/query_model/")
async def demo_query_model(
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
@example_api.post("/body/")
async def demo_json_body(
    item: Item,
    item2: Annotated[int, Body()],
):
    return item, item2


# {
#   "item":3,
#   "item2": 4
# }
# return [3, 4]
@example_api.post("/body_2single/")
async def demo_body_two_scalars(item: Annotated[int, Body()], item2: int = Body()):
    return item, item2


# 如果没有embed=True，由于类型标注为int，传入json只能是数字 33
# 有embed=True，传入 {"data":33}后，data=33
@example_api.post("/body_1single/")
async def demo_body_embedded_scalar(data: Annotated[int, Body(embed=True)]):
    return data


@example_api.post("/upload/")
async def demo_upload_files(
    files: list[UploadFile],
    template_ids: Annotated[list[int], Form()],
):
    """
    POST http://127.0.0.1:8000/example/upload/
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


@example_api.post("/raw_body")
async def demo_raw_body(request: Request):
    body = await request.body()
    return jsonable_encoder(body)


@example_api.post("/raw_form")
async def demo_raw_form(request: Request):
    form = await request.form()
    # template_ids = form.getlist("template_ids")
    return {}
