class ApiException(Exception):
    def __init__(self, msg: str, status_code: int = 400) -> None:
        super().__init__(msg)
        self.msg = msg
        self.status_code = status_code
