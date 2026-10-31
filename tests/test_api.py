import pytest
from fastapi.testclient import TestClient

from app import main


@pytest.fixture(autouse=True)
def enable_local_demo_for_existing_api_contract_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_PRODUCT_LAB_ENABLE_UNAUTHENTICATED_DEMO", "1")


def client() -> TestClient:
    main.record_store = main.InMemoryRecordStore()
    return TestClient(main.app)


def payload(external_id: str | None = "row-1", **changes: str) -> dict:
    record = {
        "source": "csv_import",
        "external_id": external_id,
        "email": "Person@Example.com ",
        "first_name": "Asha",
        "last_name": "Rao",
    }
    record.update(changes)
    return {"records": [record]}


def test_ingest_endpoint_creates_then_replays_without_duplicate() -> None:
    api = client()
    created = api.post("/v1/ingest", json=payload())
    replay = api.post("/v1/ingest", json=payload())
    assert created.status_code == 200
    assert created.json()["created"] == 1
    assert replay.status_code == 200
    assert replay.json()["unchanged"] == 1
    assert replay.json()["created"] == 0
    assert len(main.record_store.all()) == 1


def test_ingest_endpoint_updates_same_source_identity() -> None:
    api = client()
    api.post("/v1/ingest", json=payload())
    updated = api.post("/v1/ingest", json=payload(company="Acme"))
    assert updated.status_code == 200
    assert updated.json()["updated"] == 1
    assert main.record_store.get("csv_import", "row-1").company == "Acme"


def test_ingest_endpoint_reports_missing_id_as_domain_rejection() -> None:
    api = client()
    response = api.post("/v1/ingest", json=payload(external_id=None))
    assert response.status_code == 200
    body = response.json()
    assert body["rejected"] == 1
    assert body["items"][0]["reason"] == "external_id_required_for_idempotency"


def test_ingest_endpoint_rejects_invalid_request_shape() -> None:
    api = client()
    response = api.post("/v1/ingest", json={"records": "not-a-list"})
    assert response.status_code == 422


def test_ingest_endpoint_reports_blank_source_as_domain_rejection() -> None:
    api = client()
    response = api.post("/v1/ingest", json=payload(source="  "))
    assert response.status_code == 200
    body = response.json()
    assert body["rejected"] == 1
    assert body["items"][0]["reason"] == "source_required"
    assert main.record_store.all() == []


def test_unsafe_api_routes_fail_closed_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_PRODUCT_LAB_ENABLE_UNAUTHENTICATED_DEMO")
    api = client()
    assert api.post("/v1/ingest", json=payload()).status_code == 503
    assert api.post(
        "/v1/resolve", json={"incoming": {"source": "crm"}, "candidates": []}
    ).status_code == 503
    assert api.get("/health").status_code == 200
    assert main.record_store.all() == []


@pytest.mark.parametrize("flag", ["", "true", "0", "yes", " 1"])
def test_only_exact_opt_in_enables_unsafe_api(
    monkeypatch: pytest.MonkeyPatch, flag: str
) -> None:
    monkeypatch.setenv("AI_PRODUCT_LAB_ENABLE_UNAUTHENTICATED_DEMO", flag)
    assert client().post("/v1/ingest", json=payload()).status_code == 503


def test_ingestion_rejects_oversized_batch_without_partial_writes() -> None:
    api = client()
    records = [{"source": "crm", "external_id": f"row-{i}"} for i in range(1001)]
    response = api.post("/v1/ingest", json={"records": records})
    assert response.status_code == 422
    assert main.record_store.all() == []


def test_resolver_rejects_oversized_candidate_list() -> None:
    api = client()
    candidates = [{"source": "crm"} for _ in range(1001)]
    response = api.post(
        "/v1/resolve", json={"incoming": {"source": "crm"}, "candidates": candidates}
    )
    assert response.status_code == 422


def test_ingestion_accepts_exact_batch_limit() -> None:
    api = client()
    records = [{"source": "crm", "external_id": f"row-{i}"} for i in range(1000)]
    response = api.post("/v1/ingest", json={"records": records})
    assert response.status_code == 200
    assert response.json()["created"] == 1000
    assert len(main.record_store.all()) == 1000
