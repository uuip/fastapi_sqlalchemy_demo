from dataclasses import dataclass

import pytest

from app.apps.accounts.admin import views as admin_views
from app.common.exceptions import ApiException
from app.common.security.token import Token


class RequestStub:
    def __init__(self, form_data=None, session=None):
        self._form_data = form_data or {}
        self.session = session or {}

    async def form(self):
        return self._form_data


class SessionFactoryStub:
    def __init__(self, session):
        self.session = session
        self.entered = False

    async def __aenter__(self):
        self.entered = True
        return self.session

    async def __aexit__(self, exc_type, exc, traceback):
        return False


@dataclass
class UserStub:
    id: int = 1


async def test_admin_login_rejects_missing_username_without_opening_session(monkeypatch: pytest.MonkeyPatch):
    opened_sessions = 0

    def fail_if_opened():
        nonlocal opened_sessions
        opened_sessions += 1
        raise AssertionError("session should not be opened")

    monkeypatch.setattr(admin_views, "async_session_factory", fail_if_opened)

    result = await admin_views.AdminAuth(secret_key="secret").login(RequestStub({"password": "password"}))

    assert result is False
    assert opened_sessions == 0


async def test_admin_login_stores_token_when_credentials_are_valid(monkeypatch: pytest.MonkeyPatch):
    session = object()
    session_factory = SessionFactoryStub(session)
    calls = []

    async def fake_login_user(db_session, *, username, password):
        calls.append((db_session, username, password))
        return Token(access_token="admin-token")

    monkeypatch.setattr(admin_views, "async_session_factory", lambda: session_factory)
    monkeypatch.setattr(admin_views, "login_user", fake_login_user)
    request = RequestStub({"username": "alice", "password": "password"})

    result = await admin_views.AdminAuth(secret_key="secret").login(request)

    assert result is True
    assert request.session == {"token": "admin-token"}
    assert calls == [(session, "alice", "password")]
    assert session_factory.entered is True


async def test_admin_login_returns_false_when_service_rejects_credentials(monkeypatch: pytest.MonkeyPatch):
    async def reject_login(*args, **kwargs):
        raise ApiException("bad credentials")

    monkeypatch.setattr(admin_views, "async_session_factory", lambda: SessionFactoryStub(object()))
    monkeypatch.setattr(admin_views, "login_user", reject_login)
    request = RequestStub({"username": "alice", "password": "wrong"})

    result = await admin_views.AdminAuth(secret_key="secret").login(request)

    assert result is False
    assert request.session == {}


async def test_admin_authenticate_returns_false_without_token(monkeypatch: pytest.MonkeyPatch):
    opened_sessions = 0

    def fail_if_opened():
        nonlocal opened_sessions
        opened_sessions += 1
        raise AssertionError("session should not be opened")

    monkeypatch.setattr(admin_views, "async_session_factory", fail_if_opened)

    result = await admin_views.AdminAuth(secret_key="secret").authenticate(RequestStub())

    assert result is False
    assert opened_sessions == 0


async def test_admin_authenticate_returns_true_for_valid_token(monkeypatch: pytest.MonkeyPatch):
    session = object()
    session_factory = SessionFactoryStub(session)
    calls = []

    async def fake_authenticate_token(db_session, token):
        calls.append((db_session, token))
        return UserStub()

    monkeypatch.setattr(admin_views, "async_session_factory", lambda: session_factory)
    monkeypatch.setattr(admin_views, "authenticate_token", fake_authenticate_token)

    result = await admin_views.AdminAuth(secret_key="secret").authenticate(
        RequestStub(session={"token": "admin-token"})
    )

    assert result is True
    assert calls == [(session, "admin-token")]
    assert session_factory.entered is True


async def test_admin_authenticate_returns_false_when_token_is_rejected(monkeypatch: pytest.MonkeyPatch):
    async def reject_token(*args, **kwargs):
        raise ApiException("bad token")

    monkeypatch.setattr(admin_views, "async_session_factory", lambda: SessionFactoryStub(object()))
    monkeypatch.setattr(admin_views, "authenticate_token", reject_token)

    result = await admin_views.AdminAuth(secret_key="secret").authenticate(RequestStub(session={"token": "bad"}))

    assert result is False
