from .exceptions import ApiException
from .generic import Rsp

OK = lambda data: Rsp(data=data)
ERROR = lambda msg: Rsp(code=400, msg=msg)
