import importlib
import sys


def test_deps_import_does_not_build_storage(monkeypatch):
    sys.modules.pop("app.apps.file_manager.deps", None)

    def fail_create_storage(*args, **kwargs):
        raise AssertionError("storage should be built lazily")

    monkeypatch.setattr("app.apps.file_manager.storage.create_storage", fail_create_storage)

    deps = importlib.import_module("app.apps.file_manager.deps")

    assert callable(deps.get_file_manager_context)
    assert not hasattr(deps, "create_async_engine")


def test_create_file_manager_context_uses_app_session_factory(monkeypatch):
    sys.modules.pop("app.apps.file_manager.deps", None)
    deps = importlib.import_module("app.apps.file_manager.deps")
    calls: list[str] = []
    storage_calls = []

    class DummyStorage:
        pass

    class DummySigner:
        pass

    class DummyService:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class DummySessionFactory:
        pass

    def fake_create_storage(*args, **kwargs):
        calls.append("storage")
        storage_calls.append((args, kwargs))
        return DummyStorage()

    def fake_signer(*args, **kwargs):
        calls.append("signer")
        return DummySigner()

    def fake_service(*args, **kwargs):
        calls.append("service")
        return DummyService(**kwargs)

    config = deps.FileManagerConfig(
        db_url="sqlite+aiosqlite:///:memory:",
        secret_key="test-secret",
        storage_type="local",
    )
    session_factory = DummySessionFactory()

    monkeypatch.setattr(deps, "create_storage", fake_create_storage)
    monkeypatch.setattr(deps, "FileSigner", fake_signer)
    monkeypatch.setattr(deps, "AsyncFileService", fake_service)

    monkeypatch.setattr(deps, "async_session_factory", session_factory)

    context = deps.create_file_manager_context(config=config)

    assert isinstance(context.storage, DummyStorage)
    assert isinstance(context.signer, DummySigner)
    assert isinstance(context.service, DummyService)
    assert calls == ["storage", "signer", "service"]
    assert storage_calls == [(("local",), {"root_path": "storage"})]
    assert context.service.kwargs["session_factory"] is session_factory
    assert "validator" not in context.service.kwargs


def test_create_file_manager_context_passes_s3_config_to_create_storage(monkeypatch):
    sys.modules.pop("app.apps.file_manager.deps", None)
    deps = importlib.import_module("app.apps.file_manager.deps")
    storage_calls = []

    class DummyStorage:
        pass

    class DummySigner:
        pass

    class DummyService:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    def fake_create_storage(*args, **kwargs):
        storage_calls.append((args, kwargs))
        return DummyStorage()

    config = deps.FileManagerConfig(
        db_url="sqlite+aiosqlite:///:memory:",
        secret_key="test-secret",
        storage_type="s3",
        s3_bucket_name="bucket",
        s3_region="region",
        s3_endpoint="http://s3",
        s3_access_key="access",
        s3_secret_key="secret",
        s3_address_style="path",
        s3_use_iam=True,
    )

    monkeypatch.setattr(deps, "create_storage", fake_create_storage)
    monkeypatch.setattr(deps, "FileSigner", lambda **kwargs: DummySigner())
    monkeypatch.setattr(deps, "AsyncFileService", DummyService)

    context = deps.create_file_manager_context(config=config)

    assert isinstance(context.storage, DummyStorage)
    assert storage_calls == [
        (
            ("s3",),
            {
                "bucket_name": "bucket",
                "region": "region",
                "endpoint_url": "http://s3",
                "access_key": "access",
                "secret_key": "secret",
                "address_style": "path",
                "use_iam": True,
            },
        )
    ]
