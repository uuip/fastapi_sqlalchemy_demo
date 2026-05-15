from fastapi import APIRouter, status

from app.apps.accounts.schemas.user import UserCreate, UserOut, UserPatch, UserUpdate
from app.apps.accounts.services import account as account_service
from app.common.deps import OffsetPage, OffsetPageDep, SessionDep
from app.common.exceptions import ApiException
from app.common.schemas.response import default_router_responses, error_response

users_api = APIRouter(
    prefix="/users",
    tags=["Users CRUD"],
    responses=default_router_responses()
    | {
        status.HTTP_404_NOT_FOUND: error_response(status.HTTP_404_NOT_FOUND, "User not found"),
        status.HTTP_500_INTERNAL_SERVER_ERROR: error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Database operation failed"
        ),
    },
)


@users_api.get("", response_model=OffsetPage[UserOut], summary="List users")
async def list_users(s: SessionDep, pagination: OffsetPageDep):
    return await account_service.list_accounts(s, pagination=pagination)


@users_api.get("/{user_id}", response_model=UserOut, summary="Get user")
async def get_user(user_id: int, s: SessionDep):
    user = await account_service.read_account(s, account_id=user_id)
    if user is None:
        raise ApiException("User not found", status_code=status.HTTP_404_NOT_FOUND)
    return user


@users_api.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Create user")
async def create_user(body: UserCreate, s: SessionDep):
    user = await account_service.create_account(
        s,
        username=body.username,
        password=body.password,
        energy=body.energy,
    )
    await s.commit()
    return user


@users_api.put("/{user_id}", response_model=UserOut, summary="Replace user")
async def replace_user(user_id: int, body: UserUpdate, s: SessionDep):
    user = await account_service.update_account(s, account_id=user_id, fields=body.model_dump())
    if user is None:
        raise ApiException("User not found", status_code=status.HTTP_404_NOT_FOUND)
    await s.commit()
    return user


@users_api.patch("/{user_id}", response_model=UserOut, summary="Partial update user")
async def patch_user(user_id: int, body: UserPatch, s: SessionDep):
    user = await account_service.update_account(s, account_id=user_id, fields=body.model_dump(exclude_unset=True))
    if user is None:
        raise ApiException("User not found", status_code=status.HTTP_404_NOT_FOUND)
    await s.commit()
    return user


@users_api.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete user")
async def delete_user(user_id: int, s: SessionDep):
    deleted = await account_service.delete_account(s, account_id=user_id)
    if not deleted:
        raise ApiException("User not found", status_code=status.HTTP_404_NOT_FOUND)
    await s.commit()
    return None
