from app.ingestion import InMemoryRecordStore, ingest_batch
from app.models import IntakeRecord


def record(external_id: str | None, **changes: str) -> IntakeRecord:
    values = {
        "source": "csv_import",
        "external_id": external_id,
        "email": "person@example.com",
        "first_name": "Asha",
        "last_name": "Rao",
    }
    values.update(changes)
    return IntakeRecord(**values)


def test_replaying_same_batch_is_idempotent() -> None:
    store = InMemoryRecordStore()
    batch = [record("row-1"), record("row-2", email="other@example.com")]

    first = ingest_batch(batch, store)
    replay = ingest_batch(batch, store)

    assert first.created == 2
    assert replay.unchanged == 2
    assert replay.created == 0
    assert len(store.all()) == 2


def test_same_source_identity_updates_changed_payload() -> None:
    store = InMemoryRecordStore()
    ingest_batch([record("row-1")], store)

    result = ingest_batch([record("row-1", company="Acme")], store)

    assert result.updated == 1
    assert result.created == 0
    assert store.get("csv_import", "row-1").company == "Acme"


def test_same_external_id_from_different_sources_is_not_a_collision() -> None:
    store = InMemoryRecordStore()

    result = ingest_batch(
        [
            record("42"),
            IntakeRecord(source="partner_api", external_id="42", email="person@example.com"),
        ],
        store,
    )

    assert result.created == 2
    assert len(store.all()) == 2


def test_missing_external_id_is_rejected_to_keep_retries_safe() -> None:
    store = InMemoryRecordStore()

    result = ingest_batch([record(None)], store)

    assert result.rejected == 1
    assert result.items[0].reason == "external_id_required_for_idempotency"
    assert store.all() == []


def test_mixed_batch_reports_operational_counts() -> None:
    store = InMemoryRecordStore()
    ingest_batch([record("existing")], store)

    result = ingest_batch(
        [
            record("existing"),
            record("new"),
            record(None),
        ],
        store,
    )

    assert result.total == 3
    assert result.created == 1
    assert result.unchanged == 1
    assert result.rejected == 1
