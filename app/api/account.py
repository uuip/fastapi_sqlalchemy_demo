from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.exceptions import ApiException
from app.core.logging import log_request
from app.deps import CursorPage, CursorPageDep, SessionDep, UserDep
from app.schemas import AccountSchema, Item
from app.schemas.response import Rsp, default_router_responses, error_response, openapi_error_example
from app.services import account as account_service

account_api = APIRouter(
    prefix="/account",
    dependencies=[],
    tags=["管理账户"],
    responses=default_router_responses()
    | {
        status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Database operation failed"
        ),
    },
)


@account_api.get(
    "/q",
    response_model=CursorPage[AccountSchema],
    responses={status.HTTP_400_BAD_REQUEST: error_response(status.HTTP_400_BAD_REQUEST, "demo error")},
    summary="条件查询（游标分页）",
)
@log_request()
async def query_accounts(energy: Annotated[int, Query(ge=0)], s: SessionDep, pagination: CursorPageDep):
    return await account_service.query_accounts(s, energy=energy, pagination=pagination)


@account_api.get(
    "/{id}",
    response_model=Rsp[AccountSchema],
    response_model_by_alias=False,
    responses={status.HTTP_404_NOT_FOUND: error_response(status.HTTP_404_NOT_FOUND, "Account not found")},
    summary="查询单个账户",
)
async def get_account(id: int, s: SessionDep):
    account = await account_service.read_account(s, account_id=id)
    if account is None:
        raise ApiException("Account not found", status_code=status.HTTP_404_NOT_FOUND)
    return Rsp(account)


@account_api.post(
    "/update",
    responses={
        status.HTTP_401_UNAUTHORIZED: error_response(
            status.HTTP_401_UNAUTHORIZED,
            "Could not validate credentials",
            examples={
                "missing_credentials": {
                    "summary": "Missing credentials",
                    "value": openapi_error_example(status.HTTP_401_UNAUTHORIZED, "Not authenticated"),
                },
                "invalid_credentials": {
                    "summary": "Invalid credentials",
                    "value": openapi_error_example(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials"),
                },
            },
        ),
        status.HTTP_404_NOT_FOUND: error_response(status.HTTP_404_NOT_FOUND, "Account not found"),
    },
    summary="更新单个",
)
async def update_account(item: Item, s: SessionDep, user: UserDep):
    account = await account_service.update_account(s, account_id=item.id, fields={"energy": item.energy})
    if account is None:
        raise ApiException("Account not found", status_code=status.HTTP_404_NOT_FOUND)
    await s.commit()
    return Rsp({"id": item.id, "operator": user.username})


@account_api.post("/add", response_model=Rsp[dict])
async def add_account(s: SessionDep):
    result = await account_service.create_random_account(s)
    await s.commit()
    return Rsp(result)
