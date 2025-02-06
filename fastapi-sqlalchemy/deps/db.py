from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import TypeAlias, Annotated
from urllib.parse import urlparse

from config import settings

url = urlparse(settings.db)._replace(scheme="postgresql+asyncpg").geturl()
async_db = create_async_engine(url, echo=False, pool_size=50)
async_session_factory = async_sessionmaker(bind=async_db, expire_on_commit=False)


async def async_session():
    async with async_session_factory() as s:
        yield s


SessionDep: TypeAlias = Annotated[AsyncSession, Depends(async_session)]
