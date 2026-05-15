from collections.abc import AsyncIterator
from typing import Protocol


class AsyncStorage(Protocol):
    """Async interface for file storage."""

    async def save(self, filename: str, data: bytes) -> None:
        ...

    async def save_stream(self, filename: str, chunks: AsyncIterator[bytes]) -> None:
        ...

    async def load_once(self, filename: str) -> bytes:
        ...

    def load_stream(self, filename: str) -> AsyncIterator[bytes]:
        ...

    async def download(self, filename: str, target_filepath: str) -> None:
        ...

    async def exists(self, filename: str) -> bool:
        ...

    async def delete(self, filename: str) -> None:
        ...

    async def scan(self, path: str, files: bool = True, directories: bool = False) -> list[str]:
        ...
