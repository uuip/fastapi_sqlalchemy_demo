from sqladmin import ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from app.config import settings
from app.core.db import async_session_factory
from app.core.exceptions import ApiException
from app.models import User
from app.services.auth import authenticate_token, login_user


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if not username or not password:
            return False
        try:
            async with async_session_factory() as s:
                token = await login_user(s, username=username, password=password)
        except ApiException:
            return False
        request.session.update({"token": token.access_token})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        token = request.session.get("token")
        if not token:
            return False
        try:
            async with async_session_factory() as s:
                user = await authenticate_token(s, token)
        except ApiException:
            return False
        return user is not None


authentication_backend = AdminAuth(secret_key=settings.secret_key)


class UserAdmin(ModelView, model=User):
    # SQLAdmin reads these as plain class attributes; ClassVar would break introspection.
    column_list = [User.id, User.username]  # noqa: RUF012
    column_searchable_list = [User.username]  # noqa: RUF012
