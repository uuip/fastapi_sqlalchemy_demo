import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.db import async_db
from app.core.db import async_session as api_async_session
from app.main import app
from app.models import Base, User

url = async_db.url


@pytest.fixture(scope="session")
async def async_engine():
    engine = create_async_engine(url, echo=False, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine):
    # 操作数据库的行为都需要引用此fixture
    async with async_engine.connect() as connection:
        async with connection.begin() as transaction:
            async with AsyncSession(
                bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
            ) as s:
                # Outer transaction is rolled back below for test isolation;
                # routes' commit() releases SAVEPOINTs via join_transaction_mode.
                async def override_session():
                    try:
                        yield s
                        await s.flush()
                    except Exception:
                        await s.rollback()
                        raise

                app.dependency_overrides[api_async_session] = override_session
                yield s
            await transaction.rollback()
            app.dependency_overrides.clear()


@pytest.fixture
async def client(db_session):
    # 后面测接口时，test_函数不会显式需要db_session，但需要调用db_session触发patch session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def user(db_session):
    st = insert(User).values({User.username: "username", User.password: "password"}).returning(User.id)
    user_id = await db_session.scalar(st)
    await db_session.commit()
    yield str(user_id)


@pytest.fixture(scope="session", autouse=True)
async def prepare_database():
    async_engine = create_async_engine(url)
    async with async_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    await async_engine.dispose()
    yield
