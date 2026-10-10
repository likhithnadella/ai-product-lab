from app.models import IntakeRecord
from app.search import search_records
from evals.retrieval import RetrievalCase, evaluate_retrieval


def record(source: str, external_id: str, **fields: str) -> IntakeRecord:
    return IntakeRecord(source=source, external_id=external_id, **fields)


def test_search_requires_trusted_source_scope() -> None:
    rows = [
        record("tenant-a", "1", first_name="Asha", last_name="Rao"),
        record("tenant-b", "2", first_name="Asha", last_name="Rao"),
    ]
    assert search_records(rows, "Asha", allowed_sources=frozenset()) == []
    hits = search_records(rows, "Asha", allowed_sources=frozenset({"tenant-a"}))
    assert [(hit.record.source, hit.record.external_id) for hit in hits] == [("tenant-a", "1")]


def test_all_query_terms_required_across_fields() -> None:
    rows = [
        record("crm", "1", first_name="Asha", company="Northstar"),
        record("crm", "2", first_name="Asha", company="Elsewhere"),
    ]
    hits = search_records(rows, "ASHA northstar", allowed_sources=frozenset({"crm"}))
    assert [hit.record.external_id for hit in hits] == ["1"]


def test_exact_email_ranks_above_partial_term_match() -> None:
    rows = [
        record("crm", "b", email="person@example.com"),
        record("crm", "a", first_name="person", company="example com"),
    ]
    hits = search_records(rows, "person@example.com", allowed_sources=frozenset({"crm"}))
    assert [hit.record.external_id for hit in hits] == ["b", "a"]


def test_ties_are_deterministic_and_limit_applies() -> None:
    rows = [
        record("crm", "z", first_name="Asha"),
        record("crm", "a", first_name="Asha"),
    ]
    hits = search_records(rows, "asha", allowed_sources=frozenset({"crm"}), limit=1)
    assert [hit.record.external_id for hit in hits] == ["a"]


def test_empty_query_and_missing_identity_are_not_returned() -> None:
    rows = [IntakeRecord(source="crm", first_name="Asha")]
    assert search_records(rows, "", allowed_sources=frozenset({"crm"})) == []
    assert search_records(rows, "asha", allowed_sources=frozenset({"crm"})) == []


def test_invalid_limits_are_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        search_records([], "x", allowed_sources=frozenset({"crm"}), limit=0)
    with pytest.raises(ValueError):
        evaluate_retrieval([], [], k=101)


def test_retrieval_metrics_and_unjudged_cases() -> None:
    rows = [
        record("crm", "1", first_name="Asha", last_name="Rao"),
        record("crm", "2", first_name="Asha", last_name="Singh"),
    ]
    cases = [
        RetrievalCase("Asha Rao", frozenset({("crm", "1")}), frozenset({"crm"})),
        RetrievalCase("no match", frozenset({("crm", "2")}), frozenset({"crm"})),
        RetrievalCase("unknown", frozenset(), frozenset({"crm"})),
    ]
    result = evaluate_retrieval(rows, cases, k=1)
    assert result["cases"] == 3
    assert result["judged_cases"] == 2
    assert result["recall_at_k"] == 0.5
    assert result["mrr_at_k"] == 0.5
    assert result["zero_result_rate"] == 2 / 3


def test_no_cases_returns_defined_zero_metrics() -> None:
    result = evaluate_retrieval([], [])
    assert result == {
        "cases": 0,
        "judged_cases": 0,
        "recall_at_k": 0.0,
        "mrr_at_k": 0.0,
        "zero_result_rate": 0.0,
    }
