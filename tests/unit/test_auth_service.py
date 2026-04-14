from dataclasses import dataclass

import pytest
from jwt import PyJWTError

from app.core.password import make_password, verify_password
from app.core.token import create_token
from app.services import auth as auth_service


class ScalarSession:
    def __init__(self, result):
        self.result = result
        self.statements = []

    async def scalar(self, statement):
        self.statements.append(statement)
        return self.result


@dataclass
class UserStub:
    id: int
    username: str
    password: str

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password)


def test_credentials_exception_uses_bearer_challenge():
    exc = auth_service.credentials_exception("bad token")

    assert exc.status_code == 401
    assert exc.msg == "bad token"
    assert exc.headers == {"WWW-Authenticate": "Bearer"}


async def test_login_user_returns_token_for_valid_password(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "secret_key", "auth-service-test-secret-padded-32b")
    user = UserStub(id=42, username="alice", password=make_password("password"))
    session = ScalarSession(user)

    token = await auth_service.login_user(session, username="alice", password="password")
    payload = auth_service.decode_token(token.access_token)

    assert token.token_type == "bearer"
    assert payload["id"] == 42
    assert len(session.statements) == 1


async def test_login_user_rejects_missing_user():
    session = ScalarSession(None)

    with pytest.raises(auth_service.ApiException) as exc_info:
        await auth_service.login_user(session, username="missing", password="password")

    assert exc_info.value.status_code == 401
    assert exc_info.value.msg == "Incorrect username or password"


async def test_login_user_rejects_wrong_password():
    user = UserStub(id=1, username="alice", password=make_password("password"))
    session = ScalarSession(user)

    with pytest.raises(auth_service.ApiException) as exc_info:
        await auth_service.login_user(session, username="alice", password="wrong")

    assert exc_info.value.status_code == 401
    assert exc_info.value.msg == "Incorrect username or password"


async def test_authenticate_token_returns_user_for_valid_token(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "secret_key", "auth-service-test-secret-padded-32b")
    user = UserStub(id=7, username="alice", password=make_password("password"))
    session = ScalarSession(user)
    token = create_token({"id": user.id}).access_token

    result = await auth_service.authenticate_token(session, token)

    assert result is user


async def test_authenticate_token_rejects_invalid_token():
    session = ScalarSession(None)

    with pytest.raises(auth_service.ApiException) as exc_info:
        await auth_service.authenticate_token(session, "not-a-jwt")

    assert exc_info.value.status_code == 401
    assert exc_info.value.msg == "Could not validate credentials"


async def test_authenticate_token_rejects_token_without_user_id(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "secret_key", "auth-service-test-secret-padded-32b")
    session = ScalarSession(None)
    token = create_token({"sub": "alice"}).access_token

    with pytest.raises(auth_service.ApiException) as exc_info:
        await auth_service.authenticate_token(session, token)

    assert exc_info.value.status_code == 401


async def test_authenticate_token_rejects_missing_user(monkeypatch):
    monkeypatch.setattr(auth_service.settings, "secret_key", "auth-service-test-secret-padded-32b")
    session = ScalarSession(None)
    token = create_token({"id": 999}).access_token

    with pytest.raises(auth_service.ApiException) as exc_info:
        await auth_service.authenticate_token(session, token)

    assert exc_info.value.status_code == 401


async def test_authenticate_token_propagates_decode_errors_as_unauthorized(monkeypatch):
    def raise_jwt_error(token):
        raise PyJWTError("bad token")

    monkeypatch.setattr(auth_service, "decode_token", raise_jwt_error)
    session = ScalarSession(None)

    with pytest.raises(auth_service.ApiException) as exc_info:
        await auth_service.authenticate_token(session, "bad")

    assert exc_info.value.status_code == 401
