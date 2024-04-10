from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Rsp(BaseModel, Generic[T]):
    code: int = Field(200, description="response code")
    msg: str = Field("success", description="response description message")
    data: Optional[T] = Field(None, description="response data")


class ErrRsp(BaseModel, Generic[T]):
    code: int = Field(400, description="response code")
    msg: str = Field("failed", description="response description message")
