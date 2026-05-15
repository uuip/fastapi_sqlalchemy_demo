from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from loguru import logger


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
