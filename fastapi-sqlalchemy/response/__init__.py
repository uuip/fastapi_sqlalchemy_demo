from .exceptions import ApiException
from .generic import Rsp

OK = lambda data: Rsp(data=data)


def ERROR(msg: str = None, data=None) -> Rsp:
    return Rsp(code=422, msg=msg or "failed", data=data)
