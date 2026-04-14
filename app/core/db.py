from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# async_db_url = urlparse(settings.db_url)._replace(scheme="postgresql+asyncpg").geturl()
async_db_url = settings.db_url
async_db: AsyncEngine = create_async_engine(
    async_db_url,
    echo=False,
    pool_size=20,
    pool_pre_ping=True,
    pool_recycle=1800,
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
