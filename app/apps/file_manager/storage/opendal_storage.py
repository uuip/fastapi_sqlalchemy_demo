import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import aiofiles
import opendal
from dotenv import dotenv_values

from .base import AsyncStorage

logger = logging.getLogger(__name__)


def _get_opendal_kwargs(*, scheme: str, env_file_path: str = ".env", prefix: str = "OPENDAL_"):
    kwargs = {}
    config_prefix = prefix + scheme.upper() + "_"
    for key, value in os.environ.items():
        if key.startswith(config_prefix):
            kwargs[key[len(config_prefix) :].lower()] = value

    file_env_vars: dict[str, Any] = dotenv_values(env_file_path) or {}
    for key, value in file_env_vars.items():
        if key.startswith(config_prefix) and key[len(config_prefix) :].lower() not in kwargs and value:
            kwargs[key[len(config_prefix) :].lower()] = value

    return kwargs


class AsyncOpenDALStorage(AsyncStorage):
    def __init__(self, scheme: str, **kwargs):
        kwargs = kwargs or _get_opendal_kwargs(scheme=scheme)

        if scheme == "fs":
            root = kwargs.setdefault("root", "storage")
            Path(root).mkdir(parents=True, exist_ok=True)

        retry_layer = opendal.layers.RetryLayer(max_times=3, factor=2.0, jitter=True)
        self.op = opendal.AsyncOperator(scheme=scheme, **kwargs).layer(retry_layer)

    async def save(self, filename: str, data: bytes) -> None:
        await self.op.write(path=filename, bs=data)

    async def save_stream(self, filename: str, chunks: AsyncIterator[bytes]) -> None:
        async with await self.op.open(path=filename, mode="wb") as file:
            async for chunk in chunks:
                if chunk:
                    await file.write(chunk)

    async def load_once(self, filename: str) -> bytes:
        try:
            return await self.op.read(path=filename)
        except FileNotFoundError:
            raise
        except Exception as ex:
            if "not found" in str(ex).lower():
                raise FileNotFoundError("File not found") from ex
            raise

    async def load_stream(self, filename: str) -> AsyncIterator[bytes]:
        batch_size = 4096
        try:
            async with await self.op.open(path=filename, mode="rb") as file:
                while chunk := await file.read(batch_size):
                    yield chunk
        except FileNotFoundError:
            raise
        except Exception as ex:
            if "not found" in str(ex).lower():
                raise FileNotFoundError("File not found") from ex
            raise

    async def download(self, filename: str, target_filepath: str) -> None:
        async with aiofiles.open(target_filepath, "wb") as f:
            async for chunk in self.load_stream(filename):
                await f.write(chunk)

    async def exists(self, filename: str) -> bool:
        return await self.op.exists(path=filename)

    async def delete(self, filename: str) -> None:
        if await self.exists(filename):
            await self.op.delete(path=filename)

    async def scan(self, path: str, files: bool = True, directories: bool = False) -> list[str]:
        if not await self.exists(path):
            raise FileNotFoundError("Path not found")

        lister = await self.op.list(path, recursive=True)
        entries = [entry async for entry in lister]
        if files and directories:
            return [entry.path for entry in entries]
        if files:
            return [entry.path for entry in entries if not entry.metadata.is_dir]
        elif directories:
            return [entry.path for entry in entries if entry.metadata.is_dir]
        else:
            raise ValueError("At least one of files or directories must be True")
