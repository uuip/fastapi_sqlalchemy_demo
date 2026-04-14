async def test_login(user, client):
    rsp = await client.post(
        "/token/",
        json={
            "username": "username",
            "password": "password",
        },
    )
    assert rsp.status_code == 200
    assert rsp.json()["data"]["access_token"]
