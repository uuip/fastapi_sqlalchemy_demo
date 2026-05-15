import asyncio
import csv
import io
from collections.abc import AsyncIterable
from typing import Annotated

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

stream_api = APIRouter(prefix="/stream", tags=["Streaming"])


# --- Stream JSON Lines ---
# FastAPI detects AsyncIterable[PydanticModel] return type and auto-serializes
# each yielded model as a single JSON line.


class LogEntry(BaseModel):
    id: int
    message: str


@stream_api.get("/json-lines")
async def stream_json_lines() -> AsyncIterable[LogEntry]:
    for i in range(10):
        await asyncio.sleep(0.1)
        yield LogEntry(id=i, message=f"Event {i} processed")


# --- StreamingResponse ---
# Low-level: manually construct, stream raw strings or bytes.
@stream_api.get(
    "/csv",
    response_class=StreamingResponse,
    responses={200: {"content": {"text/csv": {}}}},
)
async def stream_csv():
    def generate():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "name", "score"])
        for i in range(100):
            writer.writerow([i, f"user_{i}", i * 10])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=report.csv"},
    )


# --- Server-Sent Events (SSE) ---


class Progress(BaseModel):
    percent: int
    message: str


@stream_api.get("/sse", response_class=EventSourceResponse)
async def sse_progress(
    last_event_id: Annotated[int | None, Header()] = None,
) -> AsyncIterable[ServerSentEvent]:
    start = last_event_id + 1 if last_event_id is not None else 1
    yield ServerSentEvent(comment="progress stream starts")
    for i in range(start, 11):
        await asyncio.sleep(0.3)
        yield ServerSentEvent(
            data=Progress(percent=i * 10, message=f"Processing step {i}/10"),
            event="progress",
            id=str(i),
        )
    yield ServerSentEvent(data=Progress(percent=100, message="Done"), event="done", id="final")
