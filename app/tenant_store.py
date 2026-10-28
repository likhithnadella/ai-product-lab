"""Internal tenant-scoped storage prototype; NOT an authentication boundary.

Only a trusted authentication/authorization layer may construct TenantPrincipal.
This module is deliberately not wired into the unauthenticated HTTP endpoints.
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from threading import Lock
from typing import Literal

from app.models import IntakeRecord
from app.search import SearchHit, search_records

UpsertStatus = Literal["created", "updated", "unchanged"]
_MAX_BATCH_RECORDS = 1000


@dataclass(frozen=True)
class TenantPrincipal:
    """Server-derived identity and permissions, never populated from a request body."""

    tenant_id: str
    readable_sources: frozenset[str] = field(default_factory=frozenset)
    writable_sources: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, str) or not self.tenant_id.strip():
            raise ValueError("tenant_id must be nonblank")
        if self.tenant_id != self.tenant_id.strip():
            raise ValueError("tenant_id must not contain surrounding whitespace")
        for sources in (self.readable_sources, self.writable_sources):
            if not isinstance(sources, frozenset) or any(
                not isinstance(source, str) or not source.strip() for source in sources
            ):
                raise ValueError("source permissions must be frozensets of nonblank strings")


class TenantRecordStore:
    """Process-local tenant-aware prototype; no durability or HTTP authentication.

    The storage key includes tenant identity. Authorization is checked before
    reads/writes; snapshots are copied to avoid mutating stored state by alias.
    This is not sufficient for a production multi-tenant deployment.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], IntakeRecord] = {}
        self._lock = Lock()

    @staticmethod
    def _require(principal: TenantPrincipal, source: str, *, write: bool) -> None:
        if not isinstance(principal, TenantPrincipal):
            raise PermissionError("trusted tenant principal required")
        allowed = principal.writable_sources if write else principal.readable_sources
        if source not in allowed:
            raise PermissionError("source access denied")

    def upsert(self, principal: TenantPrincipal, record: IntakeRecord) -> UpsertStatus:
        """Classify and write one record using the same checked batch boundary."""
        return self.upsert_many(principal, [record])[0]

    def upsert_many(
        self, principal: TenantPrincipal, records: Iterable[IntakeRecord]
    ) -> list[UpsertStatus]:
        """Atomically classify and write a trusted tenant's batch in one process.

        Validate all records and source permissions before changing storage.
        At most 1,000 records are accepted; excess items fail before any write.
        Duplicate keys within a batch are applied in order, under one lock.
        This does not provide durability, multi-worker transactions, or HTTP auth.
        """
        if not isinstance(principal, TenantPrincipal):
            raise PermissionError("trusted tenant principal required")

        # Materialize and defensively copy before taking the lock, so a bad
        # item or failed copy cannot leave earlier items partially persisted.
        prepared: list[IntakeRecord] = []
        for index, record in enumerate(records):
            if index >= _MAX_BATCH_RECORDS:
                raise ValueError(f"batch exceeds {_MAX_BATCH_RECORDS} records")
            if not isinstance(record, IntakeRecord):
                raise TypeError("batch items must be IntakeRecord instances")
            self._require(principal, record.source, write=True)
            if not record.source.strip() or not record.external_id or not record.external_id.strip():
                raise ValueError("nonblank source and external_id are required")
            prepared.append(record.model_copy(deep=True))

        statuses: list[UpsertStatus] = []
        with self._lock:
            for record in prepared:
                key = (principal.tenant_id, record.source, record.external_id)
                existing = self._records.get(key)
                if existing == record:
                    statuses.append("unchanged")
                else:
                    statuses.append("created" if existing is None else "updated")
                    self._records[key] = record
        return statuses

    def get(
        self, principal: TenantPrincipal, source: str, external_id: str
    ) -> IntakeRecord | None:
        self._require(principal, source, write=False)
        with self._lock:
            stored = self._records.get((principal.tenant_id, source, external_id))
            return stored.model_copy(deep=True) if stored is not None else None

    def search(
        self, principal: TenantPrincipal, query: str, *, limit: int = 10
    ) -> list[SearchHit]:
        if not isinstance(principal, TenantPrincipal):
            raise PermissionError("trusted tenant principal required")
        with self._lock:
            records = [
                record.model_copy(deep=True)
                for (tenant, source, _), record in self._records.items()
                if tenant == principal.tenant_id and source in principal.readable_sources
            ]
        return search_records(
            records, query, allowed_sources=principal.readable_sources, limit=limit
        )
