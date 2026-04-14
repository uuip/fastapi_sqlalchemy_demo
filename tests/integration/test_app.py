async def test_health_endpoint_supports_get_and_post(client):
    get_rsp = await client.get("/health")
    post_rsp = await client.post("/health")

    assert get_rsp.status_code == 200
    assert get_rsp.json() == {"ok": True}
    assert post_rsp.status_code == 200
    assert post_rsp.json() == {"ok": True}


async def test_openapi_schema_includes_main_demo_routes(client):
    rsp = await client.get("/openapi.json")

    assert rsp.status_code == 200
    paths = rsp.json()["paths"]
    assert "/health" in paths
    assert "/token" in paths
    assert "/account/add" in paths
    assert "/example/query-params" in paths


async def test_create_app_can_disable_openapi_schema():
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    test_app = create_app(openapi_url=None, include_admin=False)

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        rsp = await c.get("/openapi.json")

    assert rsp.status_code == 404


async def test_openapi_documents_recent_demo_routes_accurately(client):
    rsp = await client.get("/openapi.json")

    assert rsp.status_code == 200
    schema = rsp.json()
    token_schema = schema["paths"]["/token"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    csv_responses = schema["paths"]["/stream/csv"]["get"]["responses"]["200"]["content"]

    assert token_schema["$ref"].endswith("/LoginRequest")
    assert "text/csv" in csv_responses
