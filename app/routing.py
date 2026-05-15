from fastapi import APIRouter

from app.apps.accounts.router import accounts_router
from app.apps.examples.router import examples_router
from app.apps.file_manager.router import file_manager_api

api_router = APIRouter()
api_router.include_router(accounts_router)
api_router.include_router(examples_router)
api_router.include_router(file_manager_api)

__all__ = ["api_router"]
