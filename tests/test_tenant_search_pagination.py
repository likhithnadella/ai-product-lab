"""Pagination must never cross tenant or source authorization boundaries."""

import pytest

from app.models import IntakeRecord
from app.tenant_store import TenantPrincipal, TenantRecordStore


def actor(tenant: str, *, read: tuple[str, ...] = ()) -> TenantPrincipal:
    return TenantPrincipal(tenant, frozenset(read), frozenset({"crm", "erp"}))


def test_tenant_search_pages_only_include_authorized_records() -> None:
    store = TenantRecordStore()
    tenant_a = actor("synthetic-a", read=("crm",))
    tenant_b = actor("synthetic-b", read=("crm", "erp"))
    for i in range(5):
        store.upsert(
            tenant_a,
            IntakeRecord(source="crm", external_id=f"a-{i}", first_name="Sample"),
        )
    store.upsert(
        tenant_a,
        IntakeRecord(source="erp", external_id="restricted", first_name="Sample"),
    )
    store.upsert(
        tenant_b,
        IntakeRecord(source="crm", external_id="other", first_name="Sample"),
    )

    pages = [
        store.search(tenant_a, "Sample", limit=2, offset=offset)
        for offset in (0, 2, 4, 6)
    ]
    ids = [hit.record.external_id for page in pages for hit in page]
    assert ids == [f"a-{i}" for i in range(5)]
    assert pages[-1] == []
    assert store.search(tenant_b, "Sample", limit=10)[0].record.external_id == "other"


@pytest.mark.parametrize("offset", [-1, 10001, True, 1.5])
def test_invalid_offset_is_rejected(offset: object) -> None:
    store = TenantRecordStore()
    with pytest.raises(ValueError, match="offset"):
        store.search(  # type: ignore[arg-type]
            actor("synthetic-a", read=("crm",)), "Sample", offset=offset
        )


def test_no_read_permission_yields_no_results_at_any_offset() -> None:
    store = TenantRecordStore()
    writer = actor("synthetic-a")
    store.upsert(writer, IntakeRecord(source="crm", external_id="1", first_name="Sample"))
    assert store.search(writer, "Sample", offset=0) == []
    assert store.search(writer, "Sample", offset=5) == []


def test_permission_revocation_between_pages_is_applied_immediately() -> None:
    store = TenantRecordStore()
    writer = actor("synthetic-a", read=("crm", "erp"))
    store.upsert(
        writer, IntakeRecord(source="crm", external_id="crm-1", first_name="Sample")
    )
    store.upsert(
        writer, IntakeRecord(source="erp", external_id="erp-1", first_name="Sample")
    )
    first_page = store.search(writer, "Sample", limit=1, offset=0)
    assert len(first_page) == 1

    # The trusted identity adapter would construct a new principal after
    # revocation. A stale principal cannot provide real-time revocation.
    restricted = actor("synthetic-a", read=("crm",))
    all_visible = store.search(restricted, "Sample", limit=10)
    assert [hit.record.external_id for hit in all_visible] == ["crm-1"]
    assert store.search(restricted, "Sample", limit=1, offset=1) == []


def test_search_results_are_detached_from_stored_records_across_pages() -> None:
    store = TenantRecordStore()
    principal = actor("synthetic-a", read=("crm",))
    store.upsert(
        principal,
        IntakeRecord(
            source="crm", external_id="1", first_name="Sample",
            attributes={"classification": "synthetic"},
        ),
    )
    page = store.search(principal, "Sample", limit=1, offset=0)
    page[0].record.attributes["classification"] = "modified"
    assert store.search(principal, "Sample", limit=1)[0].record.attributes[
        "classification"
    ] == "synthetic"
