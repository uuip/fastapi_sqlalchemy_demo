from collections.abc import Sequence
from typing import Annotated, Self

from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class OffsetPagination(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    size: int = Field(default=10, ge=1, le=200, description="页面容量")


class OffsetPage[T](BaseModel):
    code: int = 200
    page: Annotated[int, Field(ge=1)]
    size: Annotated[int, Field(ge=1)]
    total: Annotated[int, Field(ge=0)]
    data: Sequence[T]

    @classmethod
    async def create(cls, s: AsyncSession, qs: Select, pagination: OffsetPagination) -> Self:
        size = pagination.size
        page = pagination.page
        total = await s.scalar(select(func.count()).select_from(qs.subquery()))
        data = await s.scalars(qs.limit(size).offset(page * size - size))
        return cls(total=total, data=data.all(), page=page, size=size)


type OffsetPageDep = Annotated[OffsetPagination, Depends()]
