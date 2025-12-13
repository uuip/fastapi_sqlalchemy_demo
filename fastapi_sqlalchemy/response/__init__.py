from typing import TypeVar

from .exceptions import ApiException
from .generic import Rsp

T = TypeVar("T")


def OK(data: T) -> Rsp[T]:
    return Rsp(data=data)


def ERROR(code=422, msg: str = None, data=None) -> Rsp:
    return Rsp(code=code, msg=msg or "failed", data=data)
