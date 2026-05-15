import pytest

from app.common import db


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.closed = True

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


def _patch_session_factory(monkeypatch: pytest.MonkeyPatch) -> FakeSession:
    session = FakeSession()
    monkeypatch.setattr(db, "async_session_factory", lambda: session)
    return session


async def test_async_session_does_not_commit_on_successful_scope(monkeypatch: pytest.MonkeyPatch):
    session = _patch_session_factory(monkeypatch)

    dependency = db.async_session()
    yielded = await anext(dependency)
    with pytest.raises(StopAsyncIteration):
        await anext(dependency)

    assert yielded is session
    assert session.commits == 0
    assert session.rollbacks == 0
    assert session.closed is True


async def test_async_session_rolls_back_and_reraises_dependency_exception(monkeypatch: pytest.MonkeyPatch):
    session = _patch_session_factory(monkeypatch)

    dependency = db.async_session()
    yielded = await anext(dependency)
    with pytest.raises(RuntimeError, match="boom"):
        await dependency.athrow(RuntimeError("boom"))

    assert yielded is session
    assert session.commits == 0
    assert session.rollbacks == 1
    assert session.closed is True
