"""Security-oriented retrieval regression cases for empty scopes and phone lookup."""

from app.models import IntakeRecord
from app.search import search_records
from evals.retrieval import RetrievalCase, evaluate_retrieval


def test_empty_source_scope_never_returns_matching_records() -> None:
    records = [
        IntakeRecord(
            source="crm",
            external_id="c1",
            first_name="Ada",
            phone="5551234567",
        )
    ]
    for query in ("Ada", "5551234567", "(555) 123-4567"):
        assert search_records(records, query, allowed_sources=frozenset()) == []

    cases = [
        RetrievalCase(query="Ada", relevant_keys=frozenset(), allowed_sources=frozenset()),
        RetrievalCase(
            query="5551234567",
            relevant_keys=frozenset(),
            allowed_sources=frozenset(),
        ),
    ]
    report = evaluate_retrieval(records, cases, k=1)
    assert report["cases"] == 2
    assert report["judged_cases"] == 0
    assert report["zero_result_rate"] == 1.0


def test_phone_shaped_queries_obey_source_scope() -> None:
    records = [
        IntakeRecord(source="crm", external_id="c1", phone="5551234567"),
        IntakeRecord(source="partner", external_id="p1", phone="5551234567"),
    ]
    hits = search_records(
        records,
        "(555) 123-4567",
        allowed_sources=frozenset({"crm"}),
    )
    assert [(hit.record.source, hit.record.external_id) for hit in hits] == [
        ("crm", "c1")
    ]


def test_mixed_text_and_digits_cannot_trigger_phone_suffix_match() -> None:
    records = [
        IntakeRecord(source="crm", external_id="c1", phone="5551234567")
    ]
    assert search_records(
        records,
        "Ada 5551234567",
        allowed_sources=frozenset({"crm"}),
    ) == []
