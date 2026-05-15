import logging

from loguru import logger

from app.common import logging as core_logging


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


def test_patch_loguru_pretty_converts_dict():
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(str(m)), format="{message}")

    try:
        core_logging._patch_loguru_pretty()
        core_logging.logger.info({"key": "value"})

        assert len(messages) == 1
        assert "key" in messages[0]
        assert "value" in messages[0]
    finally:
        logger.remove(sink_id)


def test_patch_loguru_pretty_converts_list():
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(str(m)), format="{message}")

    try:
        core_logging._patch_loguru_pretty()
        core_logging.logger.info([1, 2, 3])

        assert len(messages) == 1
        assert "1" in messages[0]
        assert "3" in messages[0]
    finally:
        logger.remove(sink_id)


def test_patch_loguru_pretty_leaves_string_untouched():
    messages: list[str] = []
    sink_id = logger.add(lambda m: messages.append(str(m)), format="{message}")

    try:
        core_logging._patch_loguru_pretty()
        core_logging.logger.info("plain string message")

        assert len(messages) == 1
        assert messages[0].strip() == "plain string message"
    finally:
        logger.remove(sink_id)


def test_patch_loguru_pretty_idempotent():
    core_logging._patch_loguru_pretty()
    LoggerCls = type(logger)
    first_ref = LoggerCls.info
    core_logging._patch_loguru_pretty()
    second_ref = LoggerCls.info
    assert first_ref is second_ref
