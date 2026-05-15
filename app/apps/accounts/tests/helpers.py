from httpx import AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.apps.accounts.models import User


async def create_user(
    db_session: AsyncSession,
    *,
    username: str,
    password: str = "password",
    energy: int = 100,
) -> User:
    statement = insert(User).values(username=username, password=password, energy=energy).returning(User)
    created = await db_session.scalar(statement)
    await db_session.commit()
    return created


async def login(client: AsyncClient, *, username: str, password: str = "password") -> str:
    response = await client.post("/token", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]
