"""Reproducible local-only, synthetic evidence preview.

Run: python -m app.context_demo
No HTTP endpoint, network call, model inference, or real records.
"""

from dataclasses import asdict

from app.context_preview import assemble_context
from app.models import IntakeRecord
from app.tenant_store import TenantPrincipal, TenantRecordStore


def demo_report() -> dict[str, object]:
    """Demonstrate tenant/source scoping and abstention with invented records."""
    store = TenantRecordStore()
    reader = TenantPrincipal(
        "synthetic-tenant-a",
        readable_sources=frozenset({"crm"}),
        writable_sources=frozenset({"crm", "partner"}),
    )
    other = TenantPrincipal(
        "synthetic-tenant-b",
        readable_sources=frozenset({"crm"}),
        writable_sources=frozenset({"crm"}),
    )
    store.upsert_many(reader, [
        IntakeRecord(
            source="crm", external_id="synthetic-1", first_name="Ada",
            last_name="Lovelace", company="Analytical Engines",
        ),
        IntakeRecord(source="partner", external_id="synthetic-2", first_name="Ada"),
    ])
    store.upsert(
        other, IntakeRecord(source="crm", external_id="synthetic-3", first_name="Ada")
    )
    preview = assemble_context(store, reader, "Ada")
    evidence = [asdict(item) for item in preview.evidence]
    return {
        "fixture": "synthetic-context-v1",
        "abstained": preview.abstained,
        "evidence_count": len(evidence),
        "evidence": evidence,
        "missing_query_abstained": assemble_context(store, reader, "Absent").abstained,
        "tenant_b_visible": any(item["external_id"] == "synthetic-3" for item in evidence),
        "partner_visible": any(item["source"] == "partner" for item in evidence),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(demo_report(), indent=2, sort_keys=True))
