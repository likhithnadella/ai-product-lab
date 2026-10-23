"""Security regression tests using entirely synthetic tenant and record identities."""

import pytest

from app.models import IntakeRecord
from app.tenant_store import TenantPrincipal, TenantRecordStore


def principal(tenant: str, *, read=(), write=()) -> TenantPrincipal:
    return TenantPrincipal(tenant, frozenset(read), frozenset(write))


def test_same_source_identity_isolated_across_tenants() -> None:
    store = TenantRecordStore()
    a = principal("tenant-a", read=("crm",), write=("crm",))
    b = principal("tenant-b", read=("crm",), write=("crm",))
    assert store.upsert(a, IntakeRecord(source="crm", external_id="1", first_name="Ada")) == "created"
    assert store.get(b, "crm", "1") is None
    assert store.search(b, "Ada") == []
    assert store.upsert(b, IntakeRecord(source="crm", external_id="1", first_name="Grace")) == "created"
    assert store.get(a, "crm", "1").first_name == "Ada"
    assert store.get(b, "crm", "1").first_name == "Grace"


def test_source_permissions_fail_closed_for_read_write_and_search() -> None:
    store = TenantRecordStore()
    writer = principal("tenant-a", write=("crm",))
    reader = principal("tenant-a", read=("crm",))
    denied = principal("tenant-a")
    record = IntakeRecord(source="crm", external_id="1", first_name="Ada")
    assert store.upsert(writer, record) == "created"
    with pytest.raises(PermissionError):
        store.upsert(reader, record)
    with pytest.raises(PermissionError):
        store.get(writer, "crm", "1")
    with pytest.raises(PermissionError):
        store.get(denied, "crm", "1")
    assert store.search(writer, "Ada") == []
    assert [hit.record.external_id for hit in store.search(reader, "Ada")] == ["1"]


def test_records_are_copied_at_write_read_and_search_boundaries() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    record = IntakeRecord(source="crm", external_id="1", first_name="Ada", attributes={"role": "original"})
    assert store.upsert(actor, record) == "created"
    record.attributes["role"] = "changed"
    fetched = store.get(actor, "crm", "1")
    assert fetched.attributes["role"] == "original"
    fetched.attributes["role"] = "changed"
    store.search(actor, "Ada")[0].record.attributes["role"] = "changed"
    assert store.get(actor, "crm", "1").attributes["role"] == "original"
    assert store.upsert(actor, IntakeRecord(source="crm", external_id="1", first_name="Ada", attributes={"role": "original"})) == "unchanged"


@pytest.mark.parametrize("tenant", ["", " ", " tenant", "tenant "])
def test_invalid_tenant_identity_rejected(tenant: str) -> None:
    with pytest.raises(ValueError):
        principal(tenant)


def test_untrusted_principal_is_rejected() -> None:
    store = TenantRecordStore()
    with pytest.raises(PermissionError):
        store.search(None, "Ada")  # type: ignore[arg-type]
    with pytest.raises(PermissionError):
        store.get(None, "crm", "1")  # type: ignore[arg-type]
