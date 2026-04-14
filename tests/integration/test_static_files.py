async def test_static_sample_file_is_served(client):
    rsp = await client.get("/static/sample.txt")

    assert rsp.status_code == 200
    assert rsp.text.strip()
