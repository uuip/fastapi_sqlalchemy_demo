from app.common.exceptions import ApiException


def test_default_status_code_is_400():
    exc = ApiException("something went wrong")
    assert exc.status_code == 400
    assert exc.msg == "something went wrong"


def test_custom_status_code():
    exc = ApiException("not found", status_code=404)
    assert exc.status_code == 404
    assert exc.msg == "not found"


def test_is_exception():
    exc = ApiException("error")
    assert isinstance(exc, Exception)


def test_str_representation():
    exc = ApiException("bad request")
    assert str(exc) == "bad request"
