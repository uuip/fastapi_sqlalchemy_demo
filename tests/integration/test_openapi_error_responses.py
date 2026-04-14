async def test_openapi_schema_includes_uniform_error_response_components(client):
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    assert "ErrorResponse_NoneType_" in schemas
    assert "ErrorResponse_list_ValidationErrorItem__" in schemas
    assert "ValidationErrorItem" in schemas


async def test_openapi_documents_restful_user_error_responses(client):
    response = await client.get("/openapi.json")

    schema = response.json()
    get_user_responses = schema["paths"]["/users/{user_id}"]["get"]["responses"]

    assert get_user_responses["404"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ErrorResponse_NoneType_"
    )
    assert get_user_responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ErrorResponse_list_ValidationErrorItem__"
    )


async def test_openapi_documents_auth_and_validation_error_responses(client):
    response = await client.get("/openapi.json")

    schema = response.json()
    login_responses = schema["paths"]["/token"]["post"]["responses"]
    update_responses = schema["paths"]["/account/update"]["post"]["responses"]

    assert login_responses["401"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse_NoneType_")
    assert login_responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ErrorResponse_list_ValidationErrorItem__"
    )
    assert update_responses["401"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse_NoneType_")
    assert update_responses["404"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse_NoneType_")


async def test_openapi_documents_account_query_error_responses(client):
    response = await client.get("/openapi.json")

    schema = response.json()
    query_responses = schema["paths"]["/account/q"]["get"]["responses"]

    assert query_responses["400"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse_NoneType_")
    assert query_responses["422"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/ErrorResponse_list_ValidationErrorItem__"
    )
    assert query_responses["500"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse_NoneType_")


async def test_openapi_validation_error_response_documents_data_items(client):
    response = await client.get("/openapi.json")

    schemas = response.json()["components"]["schemas"]
    validation_response = schemas["ErrorResponse_list_ValidationErrorItem__"]
    data_schema = validation_response["properties"]["data"]["anyOf"][0]

    assert data_schema["type"] == "array"
    assert data_schema["items"]["$ref"].endswith("/ValidationErrorItem")


async def test_openapi_error_responses_include_runtime_shape_examples(client):
    response = await client.get("/openapi.json")

    schema = response.json()
    login_401 = schema["paths"]["/token"]["post"]["responses"]["401"]
    user_404 = schema["paths"]["/users/{user_id}"]["get"]["responses"]["404"]
    query_400 = schema["paths"]["/account/q"]["get"]["responses"]["400"]
    query_422 = schema["paths"]["/account/q"]["get"]["responses"]["422"]
    query_500 = schema["paths"]["/account/q"]["get"]["responses"]["500"]
    update_401 = schema["paths"]["/account/update"]["post"]["responses"]["401"]
    update_404 = schema["paths"]["/account/update"]["post"]["responses"]["404"]
    add_account_500 = schema["paths"]["/account/add"]["post"]["responses"]["500"]
    file_404 = schema["paths"]["/files/download/{filename}"]["get"]["responses"]["404"]

    assert login_401["content"]["application/json"]["example"] == {
        "code": 401,
        "msg": "Incorrect username or password",
    }
    assert user_404["content"]["application/json"]["example"] == {
        "code": 404,
        "msg": "User not found",
    }
    assert query_400["content"]["application/json"]["example"] == {
        "code": 400,
        "msg": "demo error",
    }
    assert query_422["content"]["application/json"]["example"]["data"][0]["loc"] == ["query", "field"]
    assert query_500["content"]["application/json"]["example"] == {
        "code": 500,
        "msg": "Database operation failed",
    }
    assert add_account_500["content"]["application/json"]["example"] == {
        "code": 500,
        "msg": "Database operation failed",
    }
    assert update_401["content"]["application/json"]["examples"]["missing_credentials"]["value"] == {
        "code": 401,
        "msg": "Not authenticated",
    }
    assert update_401["content"]["application/json"]["examples"]["invalid_credentials"]["value"] == {
        "code": 401,
        "msg": "Could not validate credentials",
    }
    assert update_404["content"]["application/json"]["example"] == {
        "code": 404,
        "msg": "Account not found",
    }
    assert file_404["content"]["application/json"]["example"] == {
        "code": 404,
        "msg": "File not found",
    }

    error_response = schema["components"]["schemas"]["ErrorResponse_NoneType_"]
    assert error_response["properties"]["data"]["type"] == "null"


async def test_openapi_validation_errors_all_use_runtime_error_response_shape(client):
    response = await client.get("/openapi.json")

    schema = response.json()
    wrong_validation_refs = []
    for path, methods in schema["paths"].items():
        # /stream/* paths intentionally skip the unified responses= override:
        # streaming media types (text/event-stream, text/csv, application/jsonl)
        # cannot share a 422 entry with application/json without polluting it.
        if path.startswith("/stream/"):
            continue
        for method, operation in methods.items():
            response_422 = operation.get("responses", {}).get("422")
            if not response_422:
                continue
            response_schema = response_422["content"]["application/json"]["schema"]
            ref = response_schema.get("$ref", "")
            if not ref.endswith("/ErrorResponse_list_ValidationErrorItem__"):
                wrong_validation_refs.append((method.upper(), path, ref))

    assert wrong_validation_refs == []


async def test_openapi_error_examples_have_code_equal_to_status(client):
    """Docs invariant: example.code MUST equal the HTTP status it sits under."""
    response = await client.get("/openapi.json")

    schema = response.json()
    mismatches: list[tuple] = []
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            for status_code, resp in operation.get("responses", {}).items():
                if not status_code.startswith(("4", "5")):
                    continue
                content = resp.get("content", {}).get("application/json", {})
                if "example" in content and content["example"].get("code") != int(status_code):
                    mismatches.append((method.upper(), path, status_code, content["example"]))
                for name, example in content.get("examples", {}).items():
                    if example["value"].get("code") != int(status_code):
                        mismatches.append((method.upper(), path, status_code, name, example["value"]))

    assert mismatches == []
