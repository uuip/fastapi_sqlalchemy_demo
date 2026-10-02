import logging
import subprocess
import sys

from loguru import logger

from app.core import logging as core_logging


def test_setup_logging_preserves_third_party_logger_methods():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from loguru import logger
from app.core.logging import setup_logging
methods = {name: getattr(type(logger), name) for name in ('info', 'debug', 'warning', 'error', 'exception')}
setup_logging()
setup_logging()
assert all(getattr(type(logger), name) is method for name, method in methods.items())
""",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_setup_logging_forwards_stdlib_to_loguru():
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(str(m)), format="{message}")

    try:
        core_logging.setup_logging()
        stdlib_logger = logging.getLogger("test_setup_logging_forward")
        stdlib_logger.setLevel(logging.INFO)
        stdlib_logger.info("hello from stdlib")

        assert any("hello from stdlib" in m for m in messages)
    finally:
        logger.remove(sink_id)


def test_explicit_pretty_logging_formats_dict():
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(str(m)), format="{message}")

    try:
        core_logging.logger.info(core_logging.pretty_data({"key": "value"}))

        assert len(messages) == 1
        assert "key" in messages[0]
        assert "value" in messages[0]
    finally:
        logger.remove(sink_id)


def test_explicit_pretty_logging_formats_list():
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(str(m)), format="{message}")

    try:
        core_logging.logger.info(core_logging.pretty_data([1, 2, 3]))

        assert len(messages) == 1
        assert "1" in messages[0]
        assert "3" in messages[0]
    finally:
        logger.remove(sink_id)


def test_explicit_pretty_logging_leaves_string_untouched():
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(str(m)), format="{message}")

    try:
        core_logging.logger.info(core_logging.pretty_data("plain string message"))

        assert len(messages) == 1
        assert messages[0].strip() == "plain string message"
    finally:
        logger.remove(sink_id)


def test_repeated_setup_logging_does_not_duplicate_forwarded_messages():
    messages = []
    sink_id = logger.add(lambda message: messages.append(str(message)), format="{message}")
    try:
        core_logging.setup_logging()
        core_logging.setup_logging()
        logging.getLogger("repeat-setup").warning("one forwarded message")
        assert sum("one forwarded message" in message for message in messages) == 1
    finally:
        logger.remove(sink_id)
