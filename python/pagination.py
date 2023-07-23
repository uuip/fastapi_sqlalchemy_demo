from pydantic import Field, BaseModel
from sqlalchemy import select, func, Select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import TypeVar, Generic, Sequence

T = TypeVar("T")


class Pagination(BaseModel):
    page: int = Field(default=1, description="页码")
    size: int = Field(default=10, description="页面容量")


class Page(BaseModel, Generic[T]):
    code: int = 200
    page: int = Field(1)
    size: int = Field(10)
    total: int = Field(0)
    data: Sequence[T]

    @classmethod
    async def create(cls, s: AsyncSession, qs: Select, pagination: Pagination) -> "Page[T]":
        size = pagination.size
        page = pagination.page
        data = await s.scalars(qs.limit(size).offset(page * size - size))
        return cls(
            # total=await s.scalar(select(func.count()).select_from(qs)),
            total=0,
            data=data.all(),
            page=page,
            size=size,
        )
