"""Internal tenant-scoped storage prototype; NOT an authentication boundary.

Only a trusted authentication/authorization layer may construct TenantPrincipal.
This module is deliberately not wired into the unauthenticated HTTP endpoints.
"""

from dataclasses import dataclass, field
from threading import Lock
from typing import Literal

from app.models import IntakeRecord
from app.search import SearchHit, search_records

UpsertStatus = Literal["created", "updated", "unchanged"]


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
        self._require(principal, record.source, write=True)
        if not record.source.strip() or not record.external_id or not record.external_id.strip():
            raise ValueError("nonblank source and external_id are required")
        key = (principal.tenant_id, record.source, record.external_id)
        with self._lock:
            existing = self._records.get(key)
            if existing == record:
                return "unchanged"
            self._records[key] = record.model_copy(deep=True)
            return "created" if existing is None else "updated"

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
