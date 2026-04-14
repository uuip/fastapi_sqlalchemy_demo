from fastapi import APIRouter

from app.api.account import account_api
from app.api.auth import token_api
from app.api.background import bg_api
from app.api.files import file_api
from app.api.param_examples import example_api
from app.api.streaming import stream_api
from app.api.users import users_api

api_router = APIRouter()
api_router.include_router(account_api)
api_router.include_router(token_api)
api_router.include_router(example_api)
api_router.include_router(bg_api)
api_router.include_router(file_api)
api_router.include_router(stream_api)
api_router.include_router(users_api)

__all__ = ["api_router"]
