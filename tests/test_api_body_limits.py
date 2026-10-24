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
