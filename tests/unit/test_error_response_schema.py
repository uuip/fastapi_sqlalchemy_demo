from http import HTTPStatus

import pytest

from app.common.schemas.response import (
    ErrorResponse,
    ValidationErrorItem,
    default_router_responses,
    error_response,
    openapi_error_example,
)


def test_error_response_exposes_uniform_error_fields():
    response = ErrorResponse(code=404, msg="Resource not found")

    assert response.model_dump() == {"code": 404, "msg": "Resource not found", "data": None}


def test_error_response_can_document_validation_error_details():
    response = ErrorResponse[list[ValidationErrorItem]](
        code=422,
        msg="Request validation error",
        data=[
            {
                "type": "greater_than_equal",
                "loc": ["query", "energy"],
                "msg": "Input should be greater than or equal to 0",
                "input": -1,
            }
        ],
    )

    assert response.model_dump()["data"][0]["loc"] == ["query", "energy"]


def test_error_response_schema_can_specialize_data_field():
    schema = ErrorResponse[list[ValidationErrorItem]].model_json_schema()

    data_schema = schema["properties"]["data"]["anyOf"][0]
    assert data_schema["type"] == "array"
    assert data_schema["items"]["$ref"].endswith("/ValidationErrorItem")


@pytest.mark.parametrize(
    "status_code",
    [400, 401, 404, 422, 500],
)
def test_error_response_description_comes_from_http_status(status_code):
    assert error_response(status_code, "x")["description"] == HTTPStatus(status_code).phrase


def test_error_response_default_msg_falls_back_to_http_status_phrase():
    assert error_response(404)["content"]["application/json"]["example"]["msg"] == HTTPStatus.NOT_FOUND.phrase


def test_error_response_example_preserves_custom_msg():
    resp = error_response(404, "Account not found")
    example = resp["content"]["application/json"]["example"]
    assert example == {"code": 404, "msg": "Account not found", "data": None}


@pytest.mark.parametrize(
    ("status_code", "msg"),
    [
        (400, "demo error"),
        (401, "Incorrect username or password"),
        (404, "User not found"),
        (422, "Request validation error"),
        (500, "Database operation failed"),
    ],
)
def test_error_response_example_code_equals_status_code(status_code, msg):
    example = error_response(status_code, msg)["content"]["application/json"]["example"]
    assert example["code"] == status_code


def test_error_response_examples_path_documents_multiple_runtime_messages():
    resp = error_response(
        401,
        "Could not validate credentials",
        examples={
            "missing_credentials": {
                "summary": "Missing credentials",
                "value": openapi_error_example(401, "Not authenticated"),
            },
            "invalid_credentials": {
                "summary": "Invalid credentials",
                "value": openapi_error_example(401, "Could not validate credentials"),
            },
        },
    )

    examples = resp["content"]["application/json"]["examples"]
    assert examples["missing_credentials"]["value"] == {
        "code": 401,
        "msg": "Not authenticated",
        "data": None,
    }
    assert examples["invalid_credentials"]["value"] == {
        "code": 401,
        "msg": "Could not validate credentials",
        "data": None,
    }


def test_default_router_responses_msg_matches_runtime_handlers():
    defaults = default_router_responses()

    assert defaults[422]["content"]["application/json"]["example"]["msg"] == "Request validation error"
    assert defaults[500]["content"]["application/json"]["example"]["msg"] == "Internal server error"


def test_default_router_responses_validation_data_items_schema():
    defaults = default_router_responses()

    assert defaults[422]["model"] is ErrorResponse[list[ValidationErrorItem]]
    data = defaults[422]["content"]["application/json"]["example"]["data"]
    assert data[0]["loc"] == ["query", "field"]
