import asyncio
import os
import subprocess
import sys
from textwrap import dedent

import pytest


@pytest.mark.parametrize("fail_during_lifespan", [False, True])
async def test_application_pool_with_real_database(async_engine, fail_during_lifespan):
    # A fresh process exercises the actual globals and lifespan without dependency overrides.
    script = dedent('''\
        import asyncio
        import sys
        from contextlib import AsyncExitStack, nullcontext
        from uuid import uuid4

        import psycopg
        import pytest
        from httpx import ASGITransport, AsyncClient
        from psycopg_pool import PoolTimeout
        from sqlalchemy import NullPool, select, text

        from app.core import db
        from app.main import app
        from app.models import User

        async def verify():
            assert db.async_pool.closed
            assert isinstance(db.async_db.pool, NullPool)
            physical_connections = {}
            expected_error = (
                pytest.raises(RuntimeError, match="shutdown-test")
                if sys.argv[1] == "1" else nullcontext()
            )
            with expected_error:
                async with app.router.lifespan_context(app):
                    await db.async_pool.wait(timeout=5)
                    assert not db.async_pool.closed
                    async with AsyncExitStack() as stack:
                        for _ in range(30):
                            connection = await stack.enter_async_context(db.async_db.connect())
                            raw = (await connection.get_raw_connection()).driver_connection
                            physical_connections[raw.info.backend_pid] = raw
                        assert len(physical_connections) == 30
                        assert db.async_pool.get_stats()["pool_available"] == 0
                        with pytest.raises(PoolTimeout):
                            await db.async_pool.getconn(timeout=0.05)
                        assert await connection.scalar(text("SHOW TimeZone")) == "Asia/Shanghai"
                    assert db.async_pool.get_stats()["pool_available"] == 30

                    # Kill an idle backend; checkout health checks must replace it before use.
                    original_backends = set(physical_connections)
                    victim = next(iter(physical_connections))
                    observer = await psycopg.AsyncConnection.connect(db.async_pool.conninfo, autocommit=True)
                    async with observer:
                        cursor = await observer.execute("SELECT pg_terminate_backend(%s)", (victim,))
                        assert (await cursor.fetchone())[0]
                    reused = set()
                    async with AsyncExitStack() as stack:
                        for _ in range(30):
                            connection = await stack.enter_async_context(db.async_db.connect())
                            pid = await connection.scalar(text("SELECT pg_backend_pid()"))
                            assert pid != victim
                            reused.add(pid)
                            raw = (await connection.get_raw_connection()).driver_connection
                            physical_connections[pid] = raw
                    assert len(reused) == 30
                    assert len(reused & original_backends) == 29
                    for _ in range(60):
                        async with db.async_db.connect() as connection:
                            pid = await connection.scalar(text("SELECT pg_backend_pid()"))
                            assert pid in reused
                    assert db.async_pool.get_stats()["pool_available"] == 30

                    username = f"pool-{uuid4().hex}"
                    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                        created = await client.post(
                            "/users", json={"username": username, "password": "password", "energy": 42}
                        )
                        assert created.status_code == 201, created.text
                        user_id = created.json()["id"]
                        login = await client.post("/token", json={"username": username, "password": "password"})
                        assert login.status_code == 200, login.text
                        assert login.json()["code"] == 200
                        client.headers["Authorization"] = "Bearer " + login.json()["data"]["access_token"]
                        updated = await client.patch(f"/users/{user_id}", json={"energy": 43})
                        assert updated.status_code == 200, updated.text
                        assert updated.json()["energy"] == 43
                        async with db.async_session_factory() as session:
                            stored = await session.scalar(select(User).where(User.id == user_id))
                            assert stored.username == username
                            assert stored.energy == 43
                            assert stored.check_password("password")

                        for abort in (False, True):
                            dependency = db.async_session()
                            session = await anext(dependency)
                            await session.execute(
                                text('UPDATE "user" SET energy=99 WHERE id=:id'), {"id": user_id}
                            )
                            if abort:
                                with pytest.raises(RuntimeError, match="rollback-test"):
                                    await dependency.athrow(RuntimeError("rollback-test"))
                            else:
                                with pytest.raises(StopAsyncIteration):
                                    await anext(dependency)
                            async with db.async_session_factory() as session:
                                assert await session.scalar(select(User.energy).where(User.id == user_id)) == 43

                        admin_login = await client.post(
                            "/admin/login", data={"username": username, "password": "password"}
                        )
                        assert admin_login.status_code == 302, admin_login.text
                        admin_list = await client.get("/admin/user/list", params={"search": username})
                        assert admin_list.status_code == 200, admin_list.text
                        assert username in admin_list.text
                        deleted = await client.delete(f"/users/{user_id}")
                        assert deleted.status_code == 204, deleted.text
                        async with db.async_session_factory() as session:
                            assert await session.get(User, user_id) is None
                    assert db.async_pool.get_stats()["pool_available"] == 30
                    if sys.argv[1] == "1":
                        raise RuntimeError("shutdown-test")
            assert db.async_pool.closed
            assert all(connection.closed for connection in physical_connections.values())
            print("pool-behavior-ok")

        asyncio.run(verify())
    ''')
    env = os.environ | {"DB_URL": async_engine.url.render_as_string(hide_password=False)}
    process = await asyncio.to_thread(
        subprocess.run,
        [sys.executable, "-c", script, "1" if fail_during_lifespan else "0"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert process.returncode == 0, process.stdout + process.stderr
    assert "pool-behavior-ok" in process.stdout
