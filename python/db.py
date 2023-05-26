from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from settings import settings

url = urlparse(settings.db)._replace(scheme="postgresql+asyncpg").geturl()
async_db = create_async_engine(url, echo=False, pool_size=50)
asessionmaker = async_sessionmaker(bind=async_db, expire_on_commit=False)


async def async_session():
    async with asessionmaker() as s:
        try:
            yield s
        except:
            await s.rollback()
            raise
        else:
            await s.commit()
