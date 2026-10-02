import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.config import settings
from migrations.ensure_db import ensure_sync_driver


async def test_migrations_backfill_nullable_times_and_match_models(async_engine, monkeypatch):
    schema = f"migration_test_{uuid4().hex}"
    base_url = ensure_sync_driver(async_engine.url.render_as_string(hide_password=False))
    schema_url = async_engine.url.update_query_dict({"options": f"-c search_path={schema} -c timezone=Asia/Shanghai"})
    monkeypatch.setattr(settings, "db_url", ensure_sync_driver(schema_url.render_as_string(hide_password=False)))

    def verify():
        maintenance = create_engine(base_url)
        engine = create_engine(settings.db_url)
        try:
            with maintenance.begin() as connection:
                connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            config = Config("alembic.ini")
            command.upgrade(config, "c4d3a1f6b2e0")
            known_time = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
            with engine.begin() as connection:
                connection.execute(
                    text(
                        'INSERT INTO "user" (username, password, created_at, updated_at) '
                        'VALUES (:name, :password, :created, :updated)'
                    ),
                    [
                        {"name": "missing-created", "password": "unused", "created": None, "updated": known_time},
                        {"name": "missing-updated", "password": "unused", "created": known_time, "updated": None},
                        {"name": "missing-both", "password": "unused", "created": None, "updated": None},
                    ],
                )

            command.upgrade(config, "head")
            command.check(config)

            with engine.connect() as connection:
                columns = {column["name"]: column for column in inspect(connection).get_columns("user")}
                assert not columns["created_at"]["nullable"]
                assert not columns["updated_at"]["nullable"]
                rows = connection.execute(text('SELECT username, created_at, updated_at FROM "user"')).all()
                assert len(rows) == 3
                for name, created, updated in rows:
                    assert created is not None
                    assert updated is not None
                    assert created == updated
                    if name != "missing-both":
                        assert created == known_time

            command.downgrade(config, "c4d3a1f6b2e0")
            with engine.connect() as connection:
                columns = {column["name"]: column for column in inspect(connection).get_columns("user")}
                assert columns["created_at"]["nullable"]
                assert columns["updated_at"]["nullable"]
        finally:
            engine.dispose()
            with maintenance.begin() as connection:
                connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            maintenance.dispose()

    await asyncio.to_thread(verify)
