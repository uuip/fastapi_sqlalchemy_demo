from collections.abc import AsyncIterator
from urllib.parse import urlparse

from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

async_db_url = urlparse(settings.db_url)._replace(scheme="postgresql").geturl()

async_pool = AsyncConnectionPool(
    conninfo=async_db_url,
    open=False,
    close_returns=True,
    min_size=20,
    max_size=30,
    check=AsyncConnectionPool.check_connection,
    max_lifetime=1800,
)
async_db: AsyncEngine = create_async_engine(
    settings.db_url,
    echo=False,
    poolclass=NullPool,
    async_creator=async_pool.getconn,
)
async_session_factory = async_sessionmaker(bind=async_db, expire_on_commit=False)


async def async_session() -> AsyncIterator[AsyncSession]:
    """Yield AsyncSession. Routes own commit; rollback-on-exception is a safety net."""
    async with async_session_factory() as s:
        try:
            yield s
        except Exception:
            await s.rollback()
            raise
