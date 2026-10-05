from collections.abc import Iterable

from app.models import BatchIngestionResult, IngestionItemResult, IntakeRecord


class InMemoryRecordStore:
    """Small repository implementation used until persistent storage lands.

    Keeping ingestion behind this interface makes the idempotency semantics testable
    now without prematurely choosing database infrastructure.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], IntakeRecord] = {}

    def get(self, source: str, external_id: str) -> IntakeRecord | None:
        return self._records.get((source, external_id))

    def put(self, record: IntakeRecord) -> None:
        if record.external_id is None:
            raise ValueError("external_id is required for persisted ingestion records")
        self._records[(record.source, record.external_id)] = record

    def all(self) -> list[IntakeRecord]:
        return list(self._records.values())


def ingest_batch(
    records: Iterable[IntakeRecord], store: InMemoryRecordStore
) -> BatchIngestionResult:
    """Upsert a batch using (source, external_id) as the idempotency key.

    Replaying an identical source record is a no-op. A later payload for the same
    source identity is an update. Records without a stable source identity are
    rejected rather than guessed at, preventing duplicate creation on retries.
    """
    items: list[IngestionItemResult] = []

    for record in records:
        if not record.external_id:
            items.append(
                IngestionItemResult(
                    source=record.source,
                    external_id=None,
                    status="rejected",
                    reason="external_id_required_for_idempotency",
                )
            )
            continue

        existing = store.get(record.source, record.external_id)
        if existing is None:
            store.put(record)
            status = "created"
        elif existing == record:
            status = "unchanged"
        else:
            store.put(record)
            status = "updated"

        items.append(
            IngestionItemResult(
                source=record.source,
                external_id=record.external_id,
                status=status,
            )
        )

    counts = {status: 0 for status in ("created", "updated", "unchanged", "rejected")}
    for item in items:
        counts[item.status] += 1

    return BatchIngestionResult(total=len(items), items=items, **counts)
