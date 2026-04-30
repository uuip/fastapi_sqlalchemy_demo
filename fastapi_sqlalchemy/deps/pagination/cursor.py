from typing import TypeVar, Generic, Sequence, TypeAlias, Annotated, Self, Optional

from fastapi import Depends
from pydantic import Field, BaseModel
from sqlalchemy import Select, Column
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class CursorPagination(BaseModel):
    """游标分页参数。
    cursor: 上一页最后一条记录的游标值（通常为主键 id），首页不传或传 None。
    size:   每页条数。
    """

    cursor: Optional[int] = Field(default=None, description="游标（上一页最后一条记录的 id），首页不传")
    size: int = Field(default=10, ge=1, description="每页条数")


class CursorPage(BaseModel, Generic[T]):
    """游标分页响应体，不含 total，避免全表 COUNT 影响性能。

    next_cursor: 下一页请求时使用的游标值（当前页最后一条记录的 id）；
                 若为 None 则表示已是最后一页。
    has_more:    是否还有下一页。
    """

    code: int = 200
    size: Annotated[int, Field(ge=1)]
    next_cursor: Optional[int] = Field(default=None, description="下一页游标，为 None 表示无更多数据")
    has_more: bool = Field(default=False, description="是否还有下一页")
    data: Sequence[T]

    @classmethod
    async def create(cls, s: AsyncSession, qs: Select, pagination: CursorPagination, *, cursor_column: Column) -> Self:
        """构建游标分页查询并返回 CursorPage。

        参数:
            s:             AsyncSession
            qs:            基础查询（已包含 where/order_by 等条件）
                           注意：qs 必须按 cursor_column 升序排列，
                           或调用方自行保证游标列的有序性。
            pagination:    CursorPagination 参数
            cursor_column: 用作游标的列对象，如 User.id
        """
        size = pagination.size
        cursor = pagination.cursor

        # 游标过滤：若有游标则只取 cursor 之后的记录
        if cursor is not None:
            qs = qs.where(cursor_column > cursor)

        # 多取一条用于判断是否还有下一页
        rows = (await s.scalars(qs.limit(size + 1))).all()

        has_more = len(rows) > size
        data = rows[:size]
        next_cursor = getattr(data[-1], cursor_column.key) if (has_more and data) else None

        return cls(size=size, next_cursor=next_cursor, has_more=has_more, data=data)


CursorPageDep: TypeAlias = Annotated[CursorPagination, Depends()]
