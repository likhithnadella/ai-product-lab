"""Contract tests for a local, non-LLM, tenant-scoped context preview.

All identifiers and records below are synthetic.
"""

import pytest

from app.context_preview import assemble_context
from app.models import IntakeRecord
from app.tenant_store import TenantPrincipal, TenantRecordStore


def actor(tenant: str, *, read=("crm",), write=("crm",)) -> TenantPrincipal:
    return TenantPrincipal(tenant, frozenset(read), frozenset(write))


def test_context_evidence_is_ranked_and_minimally_projected() -> None:
    store = TenantRecordStore()
    principal = actor("tenant-a")
    store.upsert_many(principal, [
        IntakeRecord(source="crm", external_id="b", first_name="Ada",
                     company="Analytical", email="private@example.invalid",
                     phone="4155550100", attributes={"private": "do-not-return"}),
        IntakeRecord(source="crm", external_id="a", first_name="Ada", company="Engines"),
    ])

    preview = assemble_context(store, principal, "Ada", max_hits=2)
    assert preview.abstained is False
    assert [item.external_id for item in preview.evidence] == ["a", "b"]
    assert preview.evidence[0].source == "crm"
    assert preview.evidence[0].matched_fields == ("first_name",)
    assert preview.evidence[0].fields == {"first_name": "Ada", "company": "Engines"}
    assert preview.evidence[1].fields == {"first_name": "Ada", "company": "Analytical"}
    assert "private@example.invalid" not in repr(preview)
    assert "4155550100" not in repr(preview)
    assert "do-not-return" not in repr(preview)


def test_context_never_crosses_tenant_or_source_scope() -> None:
    store = TenantRecordStore()
    a = actor("tenant-a", read=("crm",), write=("crm", "partner"))
    b = actor("tenant-b")
    store.upsert(a, IntakeRecord(source="crm", external_id="a", first_name="Ada"))
    store.upsert(a, IntakeRecord(source="partner", external_id="p", first_name="Ada"))
    store.upsert(b, IntakeRecord(source="crm", external_id="b", first_name="Ada"))

    result = assemble_context(store, a, "Ada")
    assert [(item.source, item.external_id) for item in result.evidence] == [("crm", "a")]
    assert [item.external_id for item in assemble_context(store, b, "Ada").evidence] == ["b"]
    assert assemble_context(store, actor("tenant-a", read=(), write=()), "Ada").abstained


def test_context_abstains_when_no_evidence_and_does_not_fabricate_text() -> None:
    preview = assemble_context(TenantRecordStore(), actor("tenant-a"), "Missing")
    assert preview.abstained is True
    assert preview.evidence == ()


@pytest.mark.parametrize("limit", [0, 21, True, 1.5, "2"])
def test_context_rejects_invalid_limits(limit: object) -> None:
    with pytest.raises(ValueError, match="max_hits"):
        assemble_context(TenantRecordStore(), actor("tenant-a"), "Ada", max_hits=limit)


@pytest.mark.parametrize("query", ["", "   ", None, 42])
def test_context_rejects_invalid_queries(query: object) -> None:
    with pytest.raises(ValueError, match="query"):
        assemble_context(TenantRecordStore(), actor("tenant-a"), query)


def test_context_requires_tenant_principal_even_with_no_matches() -> None:
    with pytest.raises(PermissionError, match="trusted tenant principal"):
        assemble_context(TenantRecordStore(), None, "Ada")  # type: ignore[arg-type]
