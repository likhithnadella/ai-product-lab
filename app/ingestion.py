from collections.abc import Iterable
from threading import Lock
from typing import Literal

from app.models import BatchIngestionResult, IngestionItemResult, IntakeRecord

UpsertStatus = Literal["created", "updated", "unchanged"]


class InMemoryRecordStore:
    """Process-local store with an atomic upsert boundary.

    The lock protects concurrent requests handled by threads in one process.
    It does not provide durability or coordination across worker processes.
    A database implementation must enforce the same source identity with a
    unique constraint and a transaction, not a read-then-write pair.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], IntakeRecord] = {}
        self._lock = Lock()

    def get(self, source: str, external_id: str) -> IntakeRecord | None:
        with self._lock:
            return self._records.get((source, external_id))

    def put(self, record: IntakeRecord) -> None:
        if not record.external_id:
            raise ValueError("external_id is required for persisted ingestion records")
        with self._lock:
            self._records[(record.source, record.external_id)] = record

    def upsert(self, record: IntakeRecord) -> UpsertStatus:
        """Classify and apply one source record under the same lock."""
        if not record.external_id:
            raise ValueError("external_id is required for persisted ingestion records")

        key = (record.source, record.external_id)
        with self._lock:
            existing = self._records.get(key)
            if existing is None:
                self._records[key] = record
                return "created"
            if existing == record:
                return "unchanged"
            self._records[key] = record
            return "updated"

    def all(self) -> list[IntakeRecord]:
        with self._lock:
            return list(self._records.values())


def ingest_batch(
    records: Iterable[IntakeRecord], store: InMemoryRecordStore
) -> BatchIngestionResult:
    """Upsert source records with replay-safe, per-item outcomes.

    The store owns the atomic classification/write operation. This avoids a
    race where two requests both read 'missing' and both report 'created'.
    Batches are not all-or-nothing transactions; each item is independent.
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

        status = store.upsert(record)
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
