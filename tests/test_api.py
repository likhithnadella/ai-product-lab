from fastapi.testclient import TestClient

from app import main


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
