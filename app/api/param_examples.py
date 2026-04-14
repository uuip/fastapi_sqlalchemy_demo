from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Form, Path, Query, Request, UploadFile, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from app.core.exceptions import ApiException
from app.core.logging import log_request
from app.schemas.response import default_router_responses

example_api = APIRouter(prefix="/example", tags=["Parameter Examples"], responses=default_router_responses())


class Item(BaseModel):
    name: str
    description: str | None = None


class Item2(BaseModel):
    price: float
    tax: float | None = None


class Pagination(BaseModel):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)


class UploadResult(BaseModel):
    filename: str | None
    content_type: str | None
    template_id: int


@example_api.get("/path-params/{uid}/{uid2}/{uid3}")
async def path_params(uid: int, uid2: Annotated[int, Path()], uid3: int = Path()) -> tuple[int, int, int]:
    """
    GET http://127.0.0.1:8000/example/path-params/1/2/3
    """
    return uid, uid2, uid3


@example_api.get("/query-params")
@log_request
async def query_params(
    q: str, q2: Annotated[str | None, Query(max_length=50)] = None, q3: str | None = Query(default=None, max_length=50)
) -> tuple[str, str | None, str | None]:
    """
    GET http://127.0.0.1:8000/example/query-params?q=a&q2=b&q3=c
    """
    return q, q2, q3


@example_api.get("/query-model")
async def query_model(
    query: Annotated[Pagination, Depends()], q4: Item = Depends()
) -> tuple[Pagination, Item]:  # noqa: B008
    return query, q4


# {
#   "item": {
#     "name": "string",
#     "description": "string"
#   },
#   "item2": 5
# }
@example_api.post("/json-body")
@log_request
async def json_body(item: Item, item2: Annotated[int, Body()]) -> tuple[Item, int]:
    return item, item2


# {
#   "item":3,
#   "item2": 4
# }
# return [3, 4]
@example_api.post("/scalar-body")
async def scalar_body(item: Annotated[int, Body()], item2: int = Body()) -> tuple[int, int]:
    return item, item2


# 如果没有embed=True，由于类型标注为int，传入json只能是数字 33
# 有embed=True，传入 {"data":33}后，data=33
@example_api.post("/embedded-scalar")
async def embedded_scalar(data: Annotated[int, Body(embed=True)]) -> int:
    return data


@example_api.post("/upload")
async def upload_files(files: list[UploadFile], template_ids: Annotated[list[int], Form()]) -> list[UploadResult]:
    """
    POST http://127.0.0.1:8000/example/upload
    Content-Type: multipart/form-data

    files: file1.pdf
    files: file2.pdf
    template_ids: 101
    template_ids: 102
    """
    if len(files) != len(template_ids):
        raise ApiException(
            msg=f"files ({len(files)}) and template_ids ({len(template_ids)}) length mismatch",
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return [
        UploadResult(filename=f.filename, content_type=f.content_type, template_id=tid)
        for f, tid in zip(files, template_ids, strict=True)
    ]


@example_api.post("/raw-body")
async def raw_body(request: Request) -> Any:
    body = await request.body()
    return jsonable_encoder(body)


@example_api.post("/raw-form")
async def raw_form(request: Request) -> dict[str, Any]:
    await request.form()
    # template_ids = form.getlist("template_ids")
    return {}
