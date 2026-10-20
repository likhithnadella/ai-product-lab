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


@pytest.mark.parametrize("identifier", ["", " ", "\t", "  \n  "])
def test_blank_external_identity_is_rejected(identifier: str) -> None:
    store = InMemoryRecordStore()
    outcome = ingest_batch([record(identifier)], store)
    assert outcome.rejected == 1
    assert outcome.items[0].reason == "external_id_required_for_idempotency"
    assert store.all() == []
    with pytest.raises(ValueError):
        store.put(record(identifier))
    with pytest.raises(ValueError):
        store.upsert(record(identifier))


def test_valid_external_ids_remain_opaque_and_replayable() -> None:
    store = InMemoryRecordStore()
    for identifier in (" row-1 ", "row-1", "a\\tb"):
        assert ingest_batch([record(identifier)], store).created == 1
        assert ingest_batch([record(identifier)], store).unchanged == 1
        assert store.get("csv_import", identifier).external_id == identifier
    assert len(store.all()) == 3


@pytest.mark.parametrize("source", ["", "   ", "\t"])
def test_blank_source_is_rejected_after_external_id_fix(source: str) -> None:
    store = InMemoryRecordStore()
    result = ingest_batch([record("valid-id", source=source), record("valid-id")], store)
    assert [item.status for item in result.items] == ["rejected", "created"]
    assert result.items[0].reason == "source_required"
    with pytest.raises(ValueError, match="source is required"):
        store.put(record("valid-id", source=source))
    with pytest.raises(ValueError, match="source is required"):
        store.upsert(record("valid-id", source=source))
    assert len(store.all()) == 1


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


@pytest.mark.parametrize("source", ["", "   "])
def test_store_put_and_upsert_reject_blank_source(source: str) -> None:
    store = InMemoryRecordStore()
    blank = record("row-1", source=source)

    with pytest.raises(ValueError, match="source is required"):
        store.put(blank)
    with pytest.raises(ValueError, match="source is required"):
        store.upsert(blank)

    assert store.all() == []

def test_store_copies_records_on_create_and_update() -> None:
    store = InMemoryRecordStore()
    incoming = record("row-1", attributes={"origin": "initial"})
    assert store.upsert(incoming) == "created"
    incoming.attributes["origin"] = "mutated"
    assert store.get("csv_import", "row-1").attributes["origin"] == "initial"

    updated = record("row-1", attributes={"origin": "updated"})
    assert store.upsert(updated) == "updated"
    updated.attributes["origin"] = "mutated-again"
    assert store.get("csv_import", "row-1").attributes["origin"] == "updated"


def test_store_get_and_all_do_not_expose_mutable_internal_state() -> None:
    store = InMemoryRecordStore()
    store.put(record("row-1", attributes={"team": "original"}))
    retrieved = store.get("csv_import", "row-1")
    assert retrieved is not None
    retrieved.attributes["team"] = "changed"
    snapshot = store.all()
    snapshot[0].attributes["team"] = "also-changed"
    assert store.get("csv_import", "row-1").attributes["team"] == "original"
    assert store.upsert(record("row-1", attributes={"team": "original"})) == "unchanged"


def test_mutating_input_identity_does_not_change_store_key() -> None:
    store = InMemoryRecordStore()
    incoming = record("row-1", attributes={"nested": "initial"})
    assert store.upsert(incoming) == "created"
    incoming.external_id = "row-2"
    incoming.source = "other_source"
    incoming.attributes["nested"] = "changed"
    assert store.get("csv_import", "row-1").attributes == {"nested": "initial"}
    assert store.get("other_source", "row-2") is None
    assert store.upsert(record("row-1", attributes={"nested": "initial"})) == "unchanged"


def test_mutating_retrieved_identity_does_not_change_store_key() -> None:
    store = InMemoryRecordStore()
    store.put(record("row-1"))
    retrieved = store.get("csv_import", "row-1")
    assert retrieved is not None
    retrieved.source = "changed"
    retrieved.external_id = "changed"
    assert store.get("csv_import", "row-1").external_id == "row-1"
    assert store.get("changed", "changed") is None
