import asyncio
import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, select

from app.core.password import verify_password
from app.models import User
from migrations.ensure_db import ensure_sync_driver


@pytest.mark.parametrize("provide_test_url", [False, True])
async def test_integration_suite_rejects_the_application_database(async_engine, provide_test_url):
    application_url = async_engine.url.render_as_string(hide_password=False)

    def verify():
        engine = create_engine(ensure_sync_driver(application_url))
        try:
            with engine.begin() as connection:
                # This row is committed before the subprocess so DROP TABLE cannot hide behind locks.
                connection.execute(
                    User.__table__.insert().values(username="isolation-sentinel", password="sentinel-password")
                )
            env = os.environ.copy()
            env["DB_URL"] = application_url
            if provide_test_url:
                env["TEST_DB_URL"] = application_url
            else:
                env.pop("TEST_DB_URL", None)
            process = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/integration/test_static_files.py", "-o", "addopts=", "-q"],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            assert process.returncode != 0
            assert "TEST_DB_URL" in process.stdout + process.stderr
            with engine.connect() as connection:
                password = connection.scalar(select(User.password).where(User.username == "isolation-sentinel"))
                assert password is not None
                assert verify_password("sentinel-password", password)
        finally:
            with engine.begin() as connection:
                connection.execute(User.__table__.delete().where(User.username == "isolation-sentinel"))
            engine.dispose()

    await asyncio.to_thread(verify)
