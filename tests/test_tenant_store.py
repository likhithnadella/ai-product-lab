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


def test_batch_preflight_denies_mixed_sources_without_partial_write() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    allowed = IntakeRecord(source="crm", external_id="1", first_name="Ada")
    forbidden = IntakeRecord(source="payroll", external_id="2", first_name="Grace")

    with pytest.raises(PermissionError, match="source access denied"):
        store.upsert_many(actor, [allowed, forbidden])

    assert store.get(actor, "crm", "1") is None
    assert store.search(actor, "Ada") == []


@pytest.mark.parametrize("bad_id", ["", " ", "\t"])
def test_batch_invalid_identity_rolls_back_all_items(bad_id: str) -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    valid = IntakeRecord(source="crm", external_id="1", first_name="Ada")
    invalid = IntakeRecord(source="crm", external_id=bad_id, first_name="Grace")

    with pytest.raises(ValueError, match="nonblank"):
        store.upsert_many(actor, [valid, invalid])

    assert store.get(actor, "crm", "1") is None


def test_batch_duplicate_keys_replay_in_order() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    first = IntakeRecord(source="crm", external_id="1", first_name="Ada")
    newer = IntakeRecord(source="crm", external_id="1", first_name="Grace")

    assert store.upsert_many(actor, [first, first, newer, newer]) == [
        "created", "unchanged", "updated", "unchanged"
    ]
    assert store.get(actor, "crm", "1").first_name == "Grace"
    assert store.upsert_many(actor, [newer]) == ["unchanged"]
    assert store.upsert_many(actor, []) == []


def test_batch_requires_principal_even_for_empty_input() -> None:
    store = TenantRecordStore()
    with pytest.raises(PermissionError, match="trusted tenant principal"):
        store.upsert_many(None, [])  # type: ignore[arg-type]


def test_batch_iterator_failure_cannot_partially_persist() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))

    def broken_stream():
        yield IntakeRecord(source="crm", external_id="1", first_name="Ada")
        raise RuntimeError("synthetic upstream read failed")

    with pytest.raises(RuntimeError, match="upstream"):
        store.upsert_many(actor, broken_stream())

    assert store.get(actor, "crm", "1") is None


def test_batch_copies_inputs_before_persisting() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    incoming = IntakeRecord(
        source="crm", external_id="1", first_name="Ada",
        attributes={"synthetic": "original"},
    )

    assert store.upsert_many(actor, [incoming]) == ["created"]
    incoming.attributes["synthetic"] = "mutated"
    assert store.get(actor, "crm", "1").attributes["synthetic"] == "original"


def test_batch_rejects_non_records_before_any_write() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    first = IntakeRecord(source="crm", external_id="1", first_name="Ada")

    with pytest.raises(TypeError, match="IntakeRecord"):
        store.upsert_many(actor, [first, None])  # type: ignore[list-item]

    assert store.get(actor, "crm", "1") is None


def test_batch_accepts_exactly_one_thousand_records() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    records = [
        IntakeRecord(source="crm", external_id=f"synthetic-{i}")
        for i in range(1000)
    ]

    assert store.upsert_many(actor, records) == ["created"] * 1000
    assert store.get(actor, "crm", "synthetic-999") is not None


def test_oversized_batch_preserves_existing_state_and_rejects_all_new_records() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    original = IntakeRecord(source="crm", external_id="existing", first_name="Ada")
    assert store.upsert(actor, original) == "created"
    records = [
        IntakeRecord(source="crm", external_id=f"synthetic-{i}")
        for i in range(1001)
    ]
    records[0] = IntakeRecord(source="crm", external_id="existing", first_name="Grace")

    with pytest.raises(ValueError, match="batch exceeds 1000 records"):
        store.upsert_many(actor, records)

    assert store.get(actor, "crm", "existing").first_name == "Ada"
    assert store.get(actor, "crm", "synthetic-1") is None


def test_batch_cap_stops_unbounded_iterator_without_partial_write() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    consumed = []

    def synthetic_stream():
        for i in range(10000):
            consumed.append(i)
            yield IntakeRecord(source="crm", external_id=f"synthetic-{i}")

    with pytest.raises(ValueError, match="batch exceeds 1000 records"):
        store.upsert_many(actor, synthetic_stream())

    assert len(consumed) == 1001
    assert store.get(actor, "crm", "synthetic-0") is None


class _SourceSwappingOnCopy(IntakeRecord):
    """Synthetic adversarial caller mutation during the snapshot boundary."""

    def model_copy(self, *, update=None, deep=False):
        self.source = "payroll"
        return super().model_copy(update=update, deep=deep)


def test_batch_authorizes_the_copied_record_not_a_mutable_original() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    payroll_reader = principal("tenant-a", read=("payroll",))
    allowed = IntakeRecord(source="crm", external_id="safe", first_name="Ada")
    swapped = _SourceSwappingOnCopy(
        source="crm", external_id="injected", first_name="Grace"
    )

    # A source field changed by a caller while copying must never bypass the
    # write permission decision or partially persist the preceding item.
    with pytest.raises(PermissionError, match="source access denied"):
        store.upsert_many(actor, [allowed, swapped])

    assert store.get(actor, "crm", "safe") is None
    assert store.get(payroll_reader, "payroll", "injected") is None


class _ExplodingEqualityRecord(IntakeRecord):
    """Synthetic fault injected during commit-time replay classification."""

    def __eq__(self, other: object) -> bool:
        raise RuntimeError("synthetic comparison failure")


def test_batch_commit_exception_preserves_entire_previous_state() -> None:
    store = TenantRecordStore()
    actor = principal("tenant-a", read=("crm",), write=("crm",))
    existing = _ExplodingEqualityRecord(
        source="crm", external_id="existing", first_name="Original"
    )
    assert store.upsert(actor, existing) == "created"

    with pytest.raises(RuntimeError, match="synthetic comparison failure"):
        store.upsert_many(
            actor,
            [
                IntakeRecord(source="crm", external_id="new", first_name="First"),
                IntakeRecord(source="crm", external_id="existing", first_name="Changed"),
            ],
        )

    # A later classification exception must not leave an earlier item written.
    assert store.get(actor, "crm", "new") is None
    assert store.get(actor, "crm", "existing").first_name == "Original"
