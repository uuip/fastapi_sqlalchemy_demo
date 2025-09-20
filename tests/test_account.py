from model import Account

from sqlalchemy import select
from sqlalchemy import func


async def test_add_tree(client, db_session):
    rsp = await client.post("/account/add")
    assert rsp.status_code == 200
    data = rsp.json()
    assert "id" in data["data"]


async def test_no_leftover_data(db_session):

    st = select(func.count("*")).select_from(Account)
    rst = await db_session.scalar(st)
    assert rst == 0
