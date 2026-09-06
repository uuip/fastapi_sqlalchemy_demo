import pytest
from sqlalchemy import make_url
from sqlalchemy.exc import ArgumentError

from app.config import Settings

# --- inject_db_timezone ---


def test_inject_db_timezone_rejects_invalid_url_containing_timezone():
    with pytest.raises(ArgumentError):
        Settings(db_url="invalid-timezone-url", secret_key="secret")


@pytest.mark.parametrize("driver", ["postgresql+psycopg", "kingbase+psycopg2", "mysql+pymysql"])
def test_inject_db_timezone_ignores_timezone_outside_connection_options(driver):
    raw = f"{driver}://timezone:time_zone%40pass@timezone-host/timezone_db?application_name=timezone"

    url = make_url(Settings(db_url=raw, secret_key="secret").db_url)

    assert url.username == "timezone"
    assert url.password == "time_zone@pass"
    assert url.host == "timezone-host"
    assert url.database == "timezone_db"
    assert url.query["application_name"] == "timezone"
    if driver.startswith("mysql"):
        assert url.query["init_command"] == "SET time_zone = '+08:00'"
    else:
        assert url.query["options"] == "-c timezone=Asia/Shanghai"


@pytest.mark.parametrize("options", ["-c%20%74imezone%3DUTC", "--TimeZone%3DUTC", "-cTimeZone%3DUTC"])
def test_inject_db_timezone_keeps_encoded_and_compact_postgres_timezone(options):
    raw = f"postgresql+psycopg://user:password@localhost/db?options={options}"

    assert Settings(db_url=raw, secret_key="secret").db_url == raw


@pytest.mark.parametrize("options", ["-c%20log_timezone%3DUTC", "-c%20application_name%3Dtimezone"])
def test_inject_db_timezone_ignores_unrelated_postgres_settings(options):
    raw = f"postgresql+psycopg://user:password@localhost/db?options={options}"

    url = make_url(Settings(db_url=raw, secret_key="secret").db_url)

    assert url.query["options"] == make_url(raw).query["options"] + " -c timezone=Asia/Shanghai"


def test_inject_db_timezone_merges_repeated_postgres_options():
    raw = (
        "postgresql+psycopg://user:password@localhost/db"
        "?options=-c%20statement_timeout%3D1000&options=-c%20lock_timeout%3D2000"
    )

    url = make_url(Settings(db_url=raw, secret_key="secret").db_url)

    assert url.query["options"] == "-c statement_timeout=1000 -c lock_timeout=2000 -c timezone=Asia/Shanghai"


@pytest.mark.parametrize("command", ["SET NAMES utf8mb4", "SET SESSION time_zone = '+00:00'"])
def test_inject_db_timezone_preserves_mysql_init_command(command):
    raw = (
        make_url("mysql+pymysql://user:password@localhost/db")
        .update_query_dict({"init_command": command})
        .render_as_string(hide_password=False)
    )

    assert Settings(db_url=raw, secret_key="secret").db_url == raw


def test_inject_db_timezone_keeps_encoded_mysql_timezone():
    raw = "mysql+pymysql://user:password@localhost/db?init_command=SET%20%74ime_zone%3D%27%2B00%3A00%27"

    assert Settings(db_url=raw, secret_key="secret").db_url == raw


@pytest.mark.parametrize("driver", ["postgresql+psycopg", "kingbase+psycopg2", "mysql+pymysql"])
def test_inject_db_timezone_is_idempotent(driver):
    first = Settings(db_url=f"{driver}://user:password@localhost/db", secret_key="secret").db_url

    assert Settings(db_url=first, secret_key="secret").db_url == first


def test_inject_db_timezone_preserves_other_backend_url_verbatim():
    raw = "sqlite:///./test.db?z=%2f&a=1"

    assert Settings(db_url=raw, secret_key="secret").db_url == raw


def test_inject_db_timezone_keeps_user_configured_postgres_timezone():
    raw = "postgresql+psycopg://user:password@localhost/db?options=-c%20timezone%3DUTC"

    assert Settings(db_url=raw, secret_key="secret").db_url == raw


def test_inject_db_timezone_keeps_user_options_when_timezone_present():
    raw = "postgresql+psycopg://user:password@localhost/db?options=-c%20statement_timeout%3D1000%20-c%20TimeZone%3DUTC"

    assert Settings(db_url=raw, secret_key="secret").db_url == raw


def test_inject_db_timezone_keeps_repeated_postgres_options_with_timezone():
    raw = (
        "postgresql+psycopg://user:password@localhost/db"
        "?options=-c%20timezone%3DUTC&options=-c%20statement_timeout%3D1000"
    )

    assert Settings(db_url=raw, secret_key="secret").db_url == raw


def test_inject_db_timezone_injects_default_when_postgres_options_has_no_timezone():
    settings = Settings(
        db_url="postgresql+psycopg://user:password@localhost/db?options=-c%20statement_timeout%3D1000",
        secret_key="secret",
    )

    options = make_url(settings.db_url).query["options"]

    assert options == "-c statement_timeout=1000 -c timezone=Asia/Shanghai"


def test_inject_db_timezone_mysql():
    settings = Settings(db_url="mysql://root:pass@localhost/mydb", secret_key="secret")
    url = make_url(settings.db_url)
    assert url.query["init_command"] == "SET time_zone = '+08:00'"


def test_inject_db_timezone_sqlite_untouched():
    raw = "sqlite:///./test.db"
    assert Settings(db_url=raw, secret_key="secret").db_url == raw


# --- db_dict ---


def test_db_dict_parses_full_url():
    s = Settings(db_url="postgresql://admin:pass123@db.example.com:5433/myapp", secret_key="secret")
    d = s.db_dict
    assert d["host"] == "db.example.com"
    assert d["port"] == 5433
    assert d["database"] == "myapp"
    assert d["user"] == "admin"
    assert d["password"] == "pass123"


def test_db_dict_default_port():
    s = Settings(db_url="postgresql://admin:pass@localhost/myapp", secret_key="secret")
    assert s.db_dict["port"] == 5432


# --- defaults ---


def test_jwt_expire_days_default():
    s = Settings(db_url="postgresql://u:p@localhost/db", secret_key="s")
    assert s.jwt_expire_days == 30
