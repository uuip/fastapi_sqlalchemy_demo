from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from httpx import AsyncClient
from loguru import logger
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def create_user(
    db_session: AsyncSession,
    *,
    username: str,
    password: str = "password",
    energy: int = 100,
) -> User:
    statement = insert(User).values(username=username, password=password, energy=energy).returning(User)
    created = await db_session.scalar(statement)
    await db_session.commit()
    return created


async def login(client: AsyncClient, *, username: str, password: str = "password") -> str:
    response = await client.post("/token", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


@contextmanager
def capture_log_messages(*, message_prefix: str | None = None) -> Iterator[list[str]]:
    messages: list[str] = []

    def sink(message):
        messages.append(str(message))

    def log_filter(record: dict[str, Any]) -> bool:
        return message_prefix is None or record["message"].startswith(message_prefix)

    sink_id = logger.add(sink, format="{message}", filter=log_filter)
    try:
        yield messages
    finally:
        logger.remove(sink_id)


@contextmanager
def capture_error_records() -> Iterator[list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    sink_id = logger.add(lambda message: records.append(message.record.copy()), level="ERROR")
    try:
        yield records
    finally:
        logger.remove(sink_id)
