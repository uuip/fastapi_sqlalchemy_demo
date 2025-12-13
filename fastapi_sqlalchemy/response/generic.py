from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Rsp(BaseModel, Generic[T]):
    code: int = Field(200, description="response code")
    msg: str = Field("success", description="response description message")
    data: T | None = Field(None, description="response data")
