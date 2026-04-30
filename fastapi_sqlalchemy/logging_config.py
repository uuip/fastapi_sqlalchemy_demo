import inspect
import logging

from fastapi import FastAPI
from loguru import logger

class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = inspect.currentframe(), 0
        while frame:
            filename = frame.f_code.co_filename
            is_logging = filename == logging.__file__
            is_frozen = "importlib" in filename and "_bootstrap" in filename
            if depth > 0 and not (is_logging or is_frozen):
                break
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(app: FastAPI) -> None:
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # gunicorn master configures handlers on gunicorn.* loggers and forks; the
    # worker inherits them. UvicornWorker also copies gunicorn handlers to
    # uvicorn.error/access. All four would otherwise consume records before
    # they reach root's InterceptHandler.
    for name in ("uvicorn.error", "uvicorn.access", "gunicorn.error", "gunicorn.access"):
        logging_logger = logging.getLogger(name)
        logging_logger.handlers.clear()
        logging_logger.propagate = True

