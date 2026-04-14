from fastapi.security import HTTPBasicCredentials
from sqladmin import ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from fastapi_sqlalchemy.api.auth import login as auth_login
from fastapi_sqlalchemy.config import settings
from fastapi_sqlalchemy.deps.authorization import authenticate as auth_authenticate
from fastapi_sqlalchemy.deps.db import async_session_factory
from fastapi_sqlalchemy.model import User


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username, password = form["username"], form["password"]
        data = HTTPBasicCredentials(username=username, password=password)
        async with async_session_factory() as s:
            token = await auth_login(s, data)
        request.session.update({"token": token.data.access_token})

        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")

        if not token:
            return False
        async with async_session_factory() as s:
            user = await auth_authenticate(s, token)
        if user:
            return True
        return False


authentication_backend = AdminAuth(secret_key=settings.secret_key)


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username]
    column_searchable_list = [User.username]
