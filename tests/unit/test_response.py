from pydantic import TypeAdapter

from app.schemas.response import Rsp


def test_response_model_accepts_positional_data():
    rsp = Rsp("payload")

    assert rsp.code == 200
    assert rsp.msg == "success"
    assert rsp.data == "payload"


def test_response_model_validates_mapping_with_data_field():
    adapter = TypeAdapter(Rsp[str])

    rsp = adapter.validate_python({"code": 200, "msg": "success", "data": "payload"})

    assert rsp.data == "payload"


def test_response_model_does_not_define_error_factory():
    assert not hasattr(Rsp, "error")
