from typing import TypeAlias, Annotated
from urllib.parse import urlparse

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from settings import settings

url = urlparse(settings.db)._replace(scheme="postgresql+asyncpg").geturl()
async_db = create_async_engine(url, echo=False, pool_size=50)
asessionmaker = async_sessionmaker(bind=async_db)


async def async_session():
    async with asessionmaker() as s:
        yield s


SessionDep: TypeAlias = Annotated[AsyncSession, Depends(async_session)]
