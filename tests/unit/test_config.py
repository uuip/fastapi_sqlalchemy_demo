from sqlalchemy import make_url

from app.config import Settings

# --- inject_db_timezone ---


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
