import json


async def test_gzip_middleware_compresses_large_response(client):
    rsp = await client.get("/stream/csv", headers={"Accept-Encoding": "gzip"})

    assert rsp.status_code == 200
    assert rsp.headers["content-encoding"] == "gzip"


async def test_background_task_endpoint_schedules_email(client, monkeypatch):
    calls: list[tuple[str, str]] = []

    async def fake_send_email(email: str, message: str):
        calls.append((email, message))

    monkeypatch.setattr("app.apps.examples.api.background.simulate_send_email", fake_send_email)

    rsp = await client.post("/bg/send-email", json={"email": "user@example.com"})

    assert rsp.status_code == 200
    assert rsp.json() == {"message": "Email task scheduled"}
    assert calls == [("user@example.com", "Welcome!")]


def test_simulate_send_email_is_async_to_avoid_blocking_workers():
    import inspect

    from app.apps.examples.api.background import simulate_send_email

    assert inspect.iscoroutinefunction(simulate_send_email)


async def test_file_download_endpoint_serves_static_sample(client):
    rsp = await client.get("/static-files/download/sample.txt")

    assert rsp.status_code == 200
    assert rsp.headers["content-disposition"] == 'attachment; filename="sample.txt"'
    assert rsp.text.strip()


async def test_stream_csv_returns_downloadable_csv(client):
    rsp = await client.get("/stream/csv")

    assert rsp.status_code == 200
    assert rsp.headers["content-type"].startswith("text/csv")
    assert rsp.headers["content-disposition"] == "attachment; filename=report.csv"
    assert rsp.text.splitlines()[0] == "id,name,score"


async def test_stream_json_lines_returns_each_model_as_json_line(client):
    rsp = await client.get("/stream/json-lines")

    assert rsp.status_code == 200
    assert json.loads(rsp.text.splitlines()[0]) == {"id": 0, "message": "Event 0 processed"}


async def test_sse_progress_resumes_from_last_event_id(client):
    rsp = await client.get("/stream/sse", headers={"Last-Event-ID": "8"})

    assert rsp.status_code == 200
    assert rsp.headers["content-type"].startswith("text/event-stream")
    assert "id: 9" in rsp.text
    assert "id: 8" not in rsp.text
    assert "event: done" in rsp.text
