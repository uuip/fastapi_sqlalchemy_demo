async def test_example_query_params_returns_values(client):
    rsp = await client.get("/example/query-params", params={"q": "a", "q2": "b", "q3": "c"})

    assert rsp.status_code == 200
    assert rsp.json() == ["a", "b", "c"]


async def test_example_json_body_returns_models_and_scalar_body(client):
    rsp = await client.post(
        "/example/json-body",
        json={"item": {"name": "book", "description": "demo"}, "item2": 5},
    )

    assert rsp.status_code == 200
    assert rsp.json() == [{"name": "book", "description": "demo"}, 5]


async def test_example_raw_body_returns_json_encoded_bytes(client):
    rsp = await client.post("/example/raw-body", content=b"raw-data")

    assert rsp.status_code == 200
    assert rsp.json() == "raw-data"


async def test_example_upload_returns_422_when_file_and_template_counts_differ(client):
    rsp = await client.post(
        "/example/upload",
        files=[
            ("files", ("one.txt", b"one", "text/plain")),
            ("files", ("two.txt", b"two", "text/plain")),
        ],
        data={"template_ids": "101"},
    )

    assert rsp.status_code == 422
    assert rsp.json()["msg"] == "files (2) and template_ids (1) length mismatch"
