from psycopg.conninfo import conninfo_to_dict

from app.core import db


def test_pool_preserves_decoded_timezone_options():
    parameters = conninfo_to_dict(db.async_pool.conninfo, **(db.async_pool.kwargs or {}))

    assert parameters["options"] == "-c timezone=Asia/Shanghai"
