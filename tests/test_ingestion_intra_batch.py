"""Regression tests for duplicate identities inside one ingestion batch."""

from app.ingestion import InMemoryRecordStore, ingest_batch
from app.models import IntakeRecord


def _record(source: str, external_id: str | None, company: str = "Acme") -> IntakeRecord:
    return IntakeRecord(source=source, external_id=external_id, company=company)


def test_duplicate_identity_in_one_batch_classifies_each_operation() -> None:
    store = InMemoryRecordStore()
    batch = [
        _record("crm", "1"),
        _record("crm", "1"),
        _record("crm", "1", company="Updated"),
        _record("crm", "1", company="Updated"),
    ]

    result = ingest_batch(batch, store)

    assert [item.status for item in result.items] == [
        "created",
        "unchanged",
        "updated",
        "unchanged",
    ]
    assert (result.total, result.created, result.updated, result.unchanged) == (
        4,
        1,
        1,
        2,
    )
    assert store.get("crm", "1").company == "Updated"
    assert len(store.all()) == 1


def test_rejected_item_does_not_interrupt_other_batch_writes() -> None:
    store = InMemoryRecordStore()
    result = ingest_batch(
        [
            _record("crm", "1"),
            _record("crm", None),
            _record("partner", "1"),
        ],
        store,
    )

    assert [item.status for item in result.items] == [
        "created",
        "rejected",
        "created",
    ]
    assert result.total == 3
    assert result.created == 2
    assert result.rejected == 1
    assert {(r.source, r.external_id) for r in store.all()} == {
        ("crm", "1"),
        ("partner", "1"),
    }
