from fastapi import status
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.schemas.response import ErrorResponse


class CatchAllExceptionMiddleware:
    """Pure-ASGI catch-all for uncaught exceptions.

    Sits inside CORSMiddleware so 500 responses keep CORS headers. Pure-ASGI
    (vs BaseHTTPMiddleware) so contextvars set here propagate into endpoints —
    needed for future request_id / OTel trace context.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:
            request = Request(scope, receive=receive)
            logger.opt(exception=exc).error(
                "Unhandled error: {} {}", request.method, request.url.path
            )
            if response_started:
                # Headers already sent — protocol forbids rewriting to 500.
                # Re-raise so the ASGI server (uvicorn) terminates the connection
                # cleanly instead of leaving an unfinished response.
                raise
            response = JSONResponse(
                ErrorResponse(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    msg="Internal server error",
                ).model_dump(),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            await response(scope, receive, send)
