import pytest

from app.config import Settings


@pytest.mark.parametrize(
    "raw",
    [
        "postgresql+psycopg://user:password@localhost/db",
        "postgresql+psycopg://user:p%40ss@localhost/db?options=-c%20timezone%3DAsia%2FTokyo",
        "mysql+pymysql://user:p%40ss@localhost/db?init_command=SET%20time_zone%3D%27%2B09%3A00%27",
        "sqlite:///./test.db?z=%2f&a=1",
        "invalid-timezone-url",
    ],
)
def test_db_url_preserved_verbatim(raw):
    assert Settings(db_url=raw, secret_key="secret", _env_file=None).db_url == raw


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
