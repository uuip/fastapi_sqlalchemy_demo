from .exceptions import ApiException
from .generic import Rsp, ErrRsp

OK = lambda data: Rsp(data=data)
ERROR = lambda msg: ErrRsp(code=422, msg=msg)
