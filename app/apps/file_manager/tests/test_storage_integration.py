"""Storage integration tests for file_manager backends."""

import uuid
from contextlib import suppress

import pytest

from app.apps.file_manager.config import FileManagerConfig
from app.apps.file_manager.storage import StorageType, create_storage


async def test_opendal_local_storage_round_trip_download_scan_and_delete(tmp_path):
    storage = create_storage(StorageType.LOCAL, root_path=str(tmp_path / "opendal"))
    prefix = f"integration/{uuid.uuid4()}"
    first_key = f"{prefix}/first.txt"
    second_key = f"{prefix}/nested/second.txt"

    await storage.save(first_key, b"first")
    await storage.save(second_key, b"second")

    assert await storage.exists(first_key)
    assert await storage.load_once(first_key) == b"first"
    assert b"".join([chunk async for chunk in storage.load_stream(second_key)]) == b"second"

    target = tmp_path / "downloaded.txt"
    await storage.download(first_key, str(target))
    assert target.read_bytes() == b"first"

    assert {first_key, second_key}.issubset(set(await storage.scan(prefix, files=True)))

    await storage.delete(first_key)
    assert not await storage.exists(first_key)
    with pytest.raises(FileNotFoundError):
        await storage.load_once(first_key)


async def test_s3_storage_round_trip_against_local_minio(tmp_path):
    cfg = FileManagerConfig()
    storage = create_storage(
        StorageType.S3,
        bucket_name=cfg.s3_bucket_name,
        region=cfg.s3_region,
        endpoint_url=cfg.s3_endpoint,
        access_key=cfg.s3_access_key,
        secret_key=cfg.s3_secret_key,
        address_style=cfg.s3_address_style,
        use_iam=cfg.s3_use_iam,
    )
    key = f"integration/{uuid.uuid4()}.txt"

    try:
        await storage.save(key, b"hello minio")

        assert await storage.exists(key)
        assert await storage.load_once(key) == b"hello minio"
        assert b"".join([chunk async for chunk in storage.load_stream(key)]) == b"hello minio"

        target = tmp_path / "minio-download.txt"
        await storage.download(key, str(target))
        assert target.read_bytes() == b"hello minio"
    finally:
        with suppress(Exception):
            await storage.delete(key)

    assert not await storage.exists(key)
    with pytest.raises(FileNotFoundError):
        await storage.load_once(key)
