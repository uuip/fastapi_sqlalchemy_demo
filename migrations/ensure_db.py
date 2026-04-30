"""Auto-create the target database and schema if they don't exist.

Supports PostgreSQL (including KingBase) and MySQL.
Can be run as a standalone script: python -m migrations.ensure_db
"""

import logging
import re
import sys
from urllib.parse import parse_qs, urlencode, urlparse

from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def _parse_search_path(url: str) -> str | None:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    options = qs.get("options", [""])[0]
    m = re.search(r"search_path\s*=\s*(\S+)", options)
    return m.group(1) if m else None


def _build_maintenance_url(url: str, dialect: str) -> str:
    parsed = urlparse(url)
    if dialect == "mysql":
        return parsed._replace(path="/").geturl()
    new_qs = {k: v for k, v in parse_qs(parsed.query).items() if k != "options"}
    return parsed._replace(
        path="/template1",
        query=urlencode(new_qs, doseq=True),
    ).geturl()


def _ensure_mysql(maintenance_url: str, db_name: str):
    eng = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    with eng.connect() as conn:
        result = conn.execute(
            text("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :db"),
            {"db": db_name},
        )
        if not result.first():
            logger.info("Creating MySQL database: %s", db_name)
            conn.execute(text(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
        else:
            logger.info("MySQL database already exists: %s", db_name)
    eng.dispose()


def _ensure_pg(maintenance_url: str, db_url: str, db_name: str, schema: str | None):
    eng = create_engine(maintenance_url, isolation_level="AUTOCOMMIT")
    with eng.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :db"),
            {"db": db_name},
        )
        if not result.first():
            logger.info("Creating PostgreSQL database: %s", db_name)
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        else:
            logger.info("PostgreSQL database already exists: %s", db_name)
    eng.dispose()

    if schema:
        target_eng = create_engine(db_url, isolation_level="AUTOCOMMIT")
        with target_eng.connect() as conn:
            result = conn.execute(
                text("SELECT 1 FROM information_schema.schemata WHERE schema_name = :s"),
                {"s": schema},
            )
            if not result.first():
                logger.info("Creating PostgreSQL schema: %s", schema)
                conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            else:
                logger.info("PostgreSQL schema already exists: %s", schema)
        target_eng.dispose()


def ensure_sync_driver(url: str) -> str:
    """Ensure the URL uses a synchronous driver instead of an async one."""
    parsed = urlparse(url)
    if parsed.scheme.startswith("postgres"):
        return parsed._replace(scheme="postgresql+psycopg").geturl()
    if parsed.scheme.startswith("mysql"):
        return parsed._replace(scheme="mysql+pymysql").geturl()
    return url


def ensure_database_and_schema(db_url: str):
    db_url = ensure_sync_driver(db_url)
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip("/").split("/")[0]
    if not db_name:
        return

    is_mysql = "mysql" in parsed.scheme
    dialect = "mysql" if is_mysql else "pg"
    maintenance_url = _build_maintenance_url(db_url, dialect)

    if is_mysql:
        _ensure_mysql(maintenance_url, db_name)
    else:
        schema = _parse_search_path(db_url)
        _ensure_pg(maintenance_url, db_url, db_name, schema)


if __name__ == "__main__":
    from fastapi_sqlalchemy.core.config import settings

    try:
        ensure_database_and_schema(settings.db_url)
    except Exception as e:
        logger.error("Failed to ensure database: %s", e)
        sys.exit(1)
