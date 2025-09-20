from .exceptions import ApiException
from .generic import Rsp

OK = lambda data: Rsp(data=data)


def ERROR(code=422, msg: str = None, data=None) -> Rsp:
    return Rsp(code=code, msg=msg or "failed", data=data)
