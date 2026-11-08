"""Auto-create the target database and schema if they don't exist.

Supports PostgreSQL (including KingBase) and MySQL.
Can be run as a standalone script: python -m migrations.ensure_db
"""

import logging
import re
import sys

from sqlalchemy import URL, create_engine, make_url, text
from sqlalchemy.schema import CreateSchema

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _sync_url(url: str) -> URL:
    parsed = make_url(url)
    if parsed.drivername.startswith("postgres"):
        return parsed.set(drivername="postgresql+psycopg")
    if parsed.drivername.startswith("mysql"):
        return parsed.set(drivername="mysql+pymysql")
    return parsed


def ensure_sync_driver(url: str) -> str:
    """Ensure the URL uses a synchronous driver instead of an async one."""
    parsed = _sync_url(url)
    if parsed.get_backend_name() in ("postgresql", "mysql"):
        return parsed.render_as_string(hide_password=False)
    return url


def _ensure_database(url: URL) -> None:
    db_name = url.database
    if url.get_backend_name() == "mysql":
        maintenance_url = url.set(database="")
        query = "SELECT 1 FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :db"
        suffix = " CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    else:
        maintenance_url = url.set(database="template1").difference_update_query(["options"])
        query = "SELECT 1 FROM pg_database WHERE datname = :db"
        suffix = ""

    engine = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            if conn.scalar(text(query), {"db": db_name}):
                logger.info("Database already exists: %s", db_name)
            else:
                name = conn.dialect.identifier_preparer.quote_identifier(db_name)
                conn.exec_driver_sql(f"CREATE DATABASE {name}{suffix}")
                logger.info("Created database: %s", db_name)
    finally:
        engine.dispose()


def _ensure_schema(url: URL) -> None:
    options = url.normalized_query.get("options", ("",))[0]
    match = re.search(r"search_path\s*=\s*(\S+)", options)
    if not match:
        return

    schema = match.group(1)
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(CreateSchema(schema, if_not_exists=True))
            logger.info("PostgreSQL schema ensured: %s", schema)
    finally:
        engine.dispose()


def ensure_database_and_schema(db_url: str):
    url = _sync_url(db_url)
    if not url.database:
        return

    _ensure_database(url)
    if url.get_backend_name() != "mysql":
        _ensure_schema(url)


if __name__ == "__main__":
    from app.config import settings

    try:
        ensure_database_and_schema(settings.db_url)
    except Exception as e:
        logger.error("Failed to ensure database: %s", e)
        sys.exit(1)
