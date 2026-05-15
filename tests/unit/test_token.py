from datetime import UTC, datetime, timedelta

import pytest
from jwt import PyJWTError

from app.common.security import token as token_module
from app.common.security.token import Token, create_token, decode_token


def test_token_model_defaults():
    t = Token(access_token="abc")
    assert t.access_token == "abc"
    assert t.token_type == "bearer"


def test_create_decode_roundtrip(monkeypatch):
    monkeypatch.setattr(token_module.settings, "secret_key", "test-secret-key-for-unit-tests-32b")
    data = {"sub": "user123", "role": "admin"}
    tok = create_token(data)
    decoded = decode_token(tok.access_token)
    assert decoded["sub"] == "user123"
    assert decoded["role"] == "admin"
    assert "exp" in decoded


def test_create_token_with_custom_expiry(monkeypatch):
    monkeypatch.setattr(token_module.settings, "secret_key", "test-secret-key-for-unit-tests-32b")
    before = datetime.now(UTC)
    tok = create_token({"sub": "u1"}, expires_delta=timedelta(hours=1))
    decoded = decode_token(tok.access_token)
    expire = datetime.fromtimestamp(decoded["exp"], tz=UTC)
    assert (expire - before) >= timedelta(minutes=59)
    assert (expire - before) <= timedelta(minutes=61)


def test_create_token_default_expiry(monkeypatch):
    monkeypatch.setattr(token_module.settings, "secret_key", "test-secret-key-for-unit-tests-32b")
    monkeypatch.setattr(token_module.settings, "jwt_expire_days", 7)
    before = datetime.now(UTC)
    tok = create_token({"sub": "u1"})
    decoded = decode_token(tok.access_token)
    expire = datetime.fromtimestamp(decoded["exp"], tz=UTC)
    assert (expire - before).days >= 6
    assert (expire - before).days <= 7


def test_create_token_does_not_mutate_input(monkeypatch):
    monkeypatch.setattr(token_module.settings, "secret_key", "test-secret-key-for-unit-tests-32b")
    data = {"sub": "user1"}
    create_token(data)
    assert "exp" not in data


def test_decode_invalid_token(monkeypatch):
    monkeypatch.setattr(token_module.settings, "secret_key", "test-secret-key-for-unit-tests-32b")
    with pytest.raises(PyJWTError):
        decode_token("this.is.not.a.valid.jwt")


def test_decode_token_with_wrong_secret(monkeypatch):
    monkeypatch.setattr(token_module.settings, "secret_key", "secret-a" + "-" * 24)
    tok = create_token({"sub": "u1"})
    monkeypatch.setattr(token_module.settings, "secret_key", "secret-b" + "-" * 24)
    with pytest.raises(PyJWTError):
        decode_token(tok.access_token)
