from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

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


def test_concurrent_replays_have_exactly_one_creator() -> None:
    store = InMemoryRecordStore()
    participants = 12
    barrier = Barrier(participants)

    def submit(_: int) -> str:
        barrier.wait(timeout=10)
        return ingest_batch([record("same-id")], store).items[0].status

    with ThreadPoolExecutor(max_workers=participants) as pool:
        statuses = list(pool.map(submit, range(participants)))

    assert statuses.count("created") == 1
    assert statuses.count("unchanged") == participants - 1
    assert len(store.all()) == 1


def test_concurrent_distinct_source_keys_do_not_collide() -> None:
    store = InMemoryRecordStore()
    participants = 8
    barrier = Barrier(participants)

    def submit(index: int) -> str:
        barrier.wait(timeout=10)
        source_record = record("same-id", source=f"source-{index}")
        return ingest_batch([source_record], store).items[0].status

    with ThreadPoolExecutor(max_workers=participants) as pool:
        statuses = list(pool.map(submit, range(participants)))

    assert statuses == ["created"] * participants
    assert len(store.all()) == participants


@pytest.mark.parametrize("source", ["", "   ", "\t"])
def test_blank_source_is_rejected_without_writing(source: str) -> None:
    store = InMemoryRecordStore()

    result = ingest_batch([record("row-1", source=source)], store)

    assert result.rejected == 1
    assert result.created == 0
    assert result.items[0].reason == "source_required"
    assert result.items[0].external_id == "row-1"
    assert store.all() == []


def test_blank_source_does_not_block_valid_records_in_same_batch() -> None:
    store = InMemoryRecordStore()
    batch = [record("row-1", source=" "), record("row-2")]

    result = ingest_batch(batch, store)

    assert result.rejected == 1
    assert result.created == 1
    assert [item.status for item in result.items] == ["rejected", "created"]
    assert [item.source for item in store.all()] == ["csv_import"]
