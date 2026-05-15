from http import HTTPStatus
from typing import Any

from fastapi import status
from pydantic import BaseModel, Field


class Rsp[T](BaseModel):
    code: int = Field(200, description="response code")
    msg: str = Field("success", description="response description message")
    data: T | None = Field(None, description="response data")

    def __init__(self, data=None, **kwargs):
        super().__init__(data=data, **kwargs)


class ValidationErrorItem(BaseModel):
    type: str = Field(..., description="validation error type")
    loc: list[str | int] = Field(..., description="validation error location")
    msg: str = Field(..., description="validation error message")
    input: Any | None = Field(None, description="invalid input value")
    ctx: dict[str, Any] | None = Field(None, description="validation context")
    url: str | None = Field(None, description="validation error documentation url")


class ErrorResponse[T](Rsp[T]):
    code: int = Field(..., description="error status code")
    msg: str = Field(..., description="error description message")
    data: T | None = Field(None, description="error details")


DEFAULT_VALIDATION_DATA: list[dict[str, Any]] = [
    {"type": "missing", "loc": ["query", "field"], "msg": "Field required", "input": None}
]


def openapi_error_example(status_code: int, msg: str, data: Any = None) -> dict[str, Any]:
    return {"code": status_code, "msg": msg, "data": data}


def error_response(
    status_code: int,
    msg: str | None = None,
    *,
    model: type = ErrorResponse[None],
    data: Any = None,
    examples: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build one OpenAPI response entry for an error status code.

    The rendered example body matches the runtime body produced by
    install_exception_handlers (i.e. {code, msg, data} where code == status_code).
    When msg is omitted, falls back to HTTPStatus(status_code).phrase. Pass
    examples= to render multiple runtime variants under the same status.
    """
    if msg is None:
        msg = HTTPStatus(status_code).phrase
    payload: dict[str, Any] = (
        {"examples": examples} if examples is not None else {"example": openapi_error_example(status_code, msg, data)}
    )
    return {
        "model": model,
        "description": HTTPStatus(status_code).phrase,
        "content": {"application/json": payload},
    }


def default_router_responses() -> dict[int, dict[str, Any]]:
    """Default responses= for an APIRouter that may emit a generic 500.

    Returns {422, 500} aligned with the runtime handler messages:
    - 422: 'Request validation error' with data=ValidationErrorItem[]
    - 500: 'Internal server error'
    DB-backed routers should override 500 with 'Database operation failed'.
    """
    return {
        status.HTTP_422_UNPROCESSABLE_CONTENT: error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Request validation error",
            model=ErrorResponse[list[ValidationErrorItem]],
            data=DEFAULT_VALIDATION_DATA,
        ),
        status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
        ),
    }
