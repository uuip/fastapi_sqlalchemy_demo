from dataclasses import dataclass

from fastapi.security import HTTPAuthorizationCredentials

from app.deps import auth as auth_deps


@dataclass
class UserStub:
    id: int


async def test_authenticate_passes_bearer_credentials_to_service(monkeypatch):
    calls = []
    expected_user = UserStub(id=1)

    async def fake_authenticate_token(session, token):
        calls.append((session, token))
        return expected_user

    monkeypatch.setattr(auth_deps, "authenticate_token", fake_authenticate_token)
    session = object()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="access-token")

    result = await auth_deps.authenticate(session, credentials)

    assert result is expected_user
    assert calls == [(session, "access-token")]
