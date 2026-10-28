"""HTTP body-byte limit regressions for the explicitly opt-in local demo."""

import json

import pytest
from fastapi.testclient import TestClient

from app import main

MAX_BODY_BYTES = 1024 * 1024


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AI_PRODUCT_LAB_ENABLE_UNAUTHENTICATED_DEMO", "1")
    main.record_store = main.InMemoryRecordStore()
    return TestClient(main.app)


def test_declared_oversized_body_rejected_without_ingestion(api: TestClient) -> None:
    body = json.dumps(
        {"records": [{"source": "synthetic", "external_id": "sample-1",
                      "first_name": "A" * MAX_BODY_BYTES}]}
    ).encode()
    response = api.post("/v1/ingest", content=body, headers={"content-type": "application/json"})
    assert response.status_code == 413
    assert main.record_store.all() == []


def test_streamed_oversized_body_without_content_length_is_rejected(api: TestClient) -> None:
    def body_chunks():
        yield b'{"records":['
        yield b" " * MAX_BODY_BYTES
        yield b"]}"

    response = api.post(
        "/v1/ingest",
        content=body_chunks(),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413
    assert main.record_store.all() == []


def test_exact_body_byte_limit_is_accepted(api: TestClient) -> None:
    # Pydantic ignores this harmless synthetic extra field; exercise the byte boundary.
    prefix = b'{"records":[],"padding":"'
    suffix = b'"}'
    body = prefix + b"x" * (MAX_BODY_BYTES - len(prefix) - len(suffix)) + suffix
    assert len(body) == MAX_BODY_BYTES
    response = api.post("/v1/ingest", content=body, headers={"content-type": "application/json"})
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_regular_small_ingestion_still_works(api: TestClient) -> None:
    response = api.post(
        "/v1/ingest", json={"records": [{"source": "synthetic", "external_id": "sample-2"}]}
    )
    assert response.status_code == 200
    assert response.json()["created"] == 1


@pytest.mark.parametrize("bad_length", ["bogus", "-1", "1, 2"])
def test_malformed_content_length_is_rejected(
    api: TestClient, bad_length: str
) -> None:
    response = api.post(
        "/v1/ingest",
        content=b'{"records":[]}',
        headers={"content-type": "application/json", "content-length": bad_length},
    )
    assert response.status_code == 400
    assert main.record_store.all() == []


def test_underreported_content_length_cannot_bypass_actual_byte_limit(
    api: TestClient,
) -> None:
    body = b'{"records":[' + b" " * MAX_BODY_BYTES + b"]}"
    response = api.post(
        "/v1/ingest",
        content=body,
        headers={"content-type": "application/json", "content-length": "1"},
    )
    assert response.status_code == 413
    assert main.record_store.all() == []


@pytest.mark.parametrize("path", ["/v1/ingest", "/v1/resolve"])
@pytest.mark.parametrize("flag", [None, "0", "true", "1 "])
def test_disabled_demo_rejects_before_reading_body(
    monkeypatch: pytest.MonkeyPatch, path: str, flag: str | None
) -> None:
    import asyncio

    from app.body_limit import DemoBodyLimitMiddleware

    if flag is None:
        monkeypatch.delenv("AI_PRODUCT_LAB_ENABLE_UNAUTHENTICATED_DEMO", raising=False)
    else:
        monkeypatch.setenv("AI_PRODUCT_LAB_ENABLE_UNAUTHENTICATED_DEMO", flag)

    async def downstream(scope, receive, send):
        raise AssertionError("disabled endpoint must not invoke downstream app")

    async def unread_body():
        raise AssertionError("disabled endpoint must not read request body")

    messages = []

    async def capture(message):
        messages.append(message)

    middleware = DemoBodyLimitMiddleware(downstream)
    scope = {"type": "http", "method": "POST", "path": path, "headers": []}
    asyncio.run(middleware(scope, unread_body, capture))

    assert messages[0]["type"] == "http.response.start"
    assert messages[0]["status"] == 503
    assert b"disabled" in messages[1]["body"]


def test_non_post_demo_path_is_not_intercepted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_PRODUCT_LAB_ENABLE_UNAUTHENTICATED_DEMO", raising=False)
    client = TestClient(main.app)
    assert client.get("/v1/ingest").status_code == 405
