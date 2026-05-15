from fastapi import APIRouter

from app.apps.accounts.api.account import account_api
from app.apps.accounts.api.auth import token_api
from app.apps.accounts.api.users import users_api

accounts_router = APIRouter()
accounts_router.include_router(account_api)
accounts_router.include_router(token_api)
accounts_router.include_router(users_api)

__all__ = ["accounts_router"]
