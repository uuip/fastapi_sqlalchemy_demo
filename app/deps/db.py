from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session

type SessionDep = Annotated[AsyncSession, Depends(async_session)]

__all__ = ["SessionDep"]
