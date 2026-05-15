import inspect
import json
import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import Request
from loguru import logger
from starlette.concurrency import run_in_threadpool

from app.common.utils import pretty_data


def _patch_loguru_pretty() -> None:
    """Auto pretty-print non-str first arg of logger.info/debug/... via pretty_data."""
    LoggerCls = type(logger)
    if getattr(LoggerCls, "_pretty_data_patched", False):
        return

    def make_wrapper(orig):
        @wraps(orig)
        def wrapper(self, __message, *args, **kwargs):
            if not isinstance(__message, str):
                __message = pretty_data(__message)
            if args:
                args = tuple(pretty_data(a) if isinstance(a, (dict, list)) else a for a in args)
            exception, depth, record, lazy, colors, raw, capture, _, _ = self._options
            return orig(
                self.opt(
                    exception=exception,
                    depth=depth + 1,
                    record=record,
                    lazy=lazy,
                    colors=colors,
                    raw=raw,
                    capture=capture,
                ),
                __message,
                *args,
                **kwargs,
            )

        return wrapper

    for name in ("trace", "debug", "info", "success", "warning", "error", "critical", "exception"):
        setattr(LoggerCls, name, make_wrapper(getattr(LoggerCls, name)))
    LoggerCls._pretty_data_patched = True


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


def setup_logging() -> None:
    _patch_loguru_pretty()
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # for name in ("uvicorn.error", "uvicorn.access"):
    #     logging_logger = logging.getLogger(name)
    #     logging_logger.handlers.clear()
    #     logging_logger.propagate = True


def log_request(endpoint: Callable[..., Any] | None = None) -> Callable[..., Any]:
    """Log query params (any method) and body (POST/PUT/PATCH). Use as @log_request or @log_request()."""

    def decorator(func):
        is_coroutine = inspect.iscoroutinefunction(func)
        signature = inspect.signature(func)
        request_name = next(
            (n for n, p in signature.parameters.items() if p.annotation is Request),
            None,
        )
        injected = request_name is None
        if injected:
            request_name = "_request"
            params = list(signature.parameters.values())
            insert_at = next(
                (i for i, p in enumerate(params) if p.kind is inspect.Parameter.VAR_KEYWORD),
                len(params),
            )
            request_param = inspect.Parameter(request_name, inspect.Parameter.KEYWORD_ONLY, annotation=Request)
            signature = signature.replace(parameters=[*params[:insert_at], request_param, *params[insert_at:]])

        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.pop(request_name) if injected else kwargs[request_name]
            method, path = request.method, request.url.path
            if request.query_params:
                logger.info("{} {} query: {}", method, path, dict(request.query_params))
            if method in {"POST", "PUT", "PATCH"}:
                body_bytes = await request.body()
                try:
                    logger.info("{} {} body: {}", method, path, json.loads(body_bytes))
                except json.JSONDecodeError:
                    logger.info("{} {} body (non-JSON)", method, path)
            if is_coroutine:
                return await func(*args, **kwargs)
            return await run_in_threadpool(func, *args, **kwargs)

        wrapper.__signature__ = signature
        return wrapper

    return decorator if endpoint is None else decorator(endpoint)
