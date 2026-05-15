import asyncio
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Body
from loguru import logger

from app.common.schemas.response import default_router_responses

bg_api = APIRouter(prefix="/bg", tags=["Background Tasks"], responses=default_router_responses())


async def simulate_send_email(email: str, message: str):
    await asyncio.sleep(2)
    logger.info("Email sent to {}: {}", email, message)


@bg_api.post("/send-email")
async def send_email_bg(email: Annotated[str, Body(embed=True)], background_tasks: BackgroundTasks):
    background_tasks.add_task(simulate_send_email, email, "Welcome!")
    return {"message": "Email task scheduled"}
