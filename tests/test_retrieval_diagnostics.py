"""Synthetic regression tests for per-query retrieval failure diagnostics."""

import pytest

from app.models import IntakeRecord
from app.search import SearchHit
from evals import retrieval
from evals.retrieval import RetrievalCase, evaluate_retrieval, evaluate_retrieval_detailed


def _record(source: str, external_id: str) -> IntakeRecord:
    return IntakeRecord(source=source, external_id=external_id, first_name="Ada")


def test_diagnostics_explain_ranked_hits_negatives_and_misses(monkeypatch) -> None:
    first = _record("crm", "1")
    relevant = _record("crm", "2")
    cases = [
        RetrievalCase("positive", frozenset({("crm", "2")}), frozenset({"crm"})),
        RetrievalCase("negative", frozenset(), frozenset({"crm"})),
        RetrievalCase("missed", frozenset({("crm", "2")}), frozenset({"crm"})),
    ]
    responses = {
        "positive": [SearchHit(record=first, score=10), SearchHit(record=relevant, score=9)],
        "negative": [SearchHit(record=first, score=8)],
        "missed": [],
    }
    monkeypatch.setattr(
        retrieval, "search_records",
        lambda records, query, **kwargs: responses[query],
    )

    summary, details = evaluate_retrieval_detailed([first, relevant], cases, k=2)

    assert summary == evaluate_retrieval([first, relevant], cases, k=2)
    assert summary["cases"] == 3
    assert summary["judged_cases"] == 2
    assert summary["recall_at_k"] == pytest.approx(0.5)
    assert summary["precision_at_k"] == pytest.approx(0.25)
    assert summary["mrr_at_k"] == pytest.approx(0.25)
    assert summary["false_positive_rate_on_negatives"] == 1.0
    assert summary["zero_result_rate"] == pytest.approx(1 / 3)

    assert details[0].retrieved_keys == (("crm", "1"), ("crm", "2"))
    assert details[0].unexpected_keys == (("crm", "1"),)
    assert details[0].missed_keys == ()
    assert details[0].first_relevant_rank == 2
    assert details[0].allowed_sources == ("crm",)
    assert details[1].relevant_keys == ()
    assert details[1].unexpected_keys == (("crm", "1"),)
    assert details[1].first_relevant_rank is None
    assert details[2].retrieved_keys == ()
    assert details[2].missed_keys == (("crm", "2"),)


def test_diagnostics_keep_fail_closed_scope_validation(monkeypatch) -> None:
    allowed = _record("crm", "1")
    forbidden = _record("partner", "2")
    monkeypatch.setattr(
        retrieval,
        "search_records",
        lambda *args, **kwargs: [SearchHit(record=forbidden, score=10)],
    )
    case = RetrievalCase("Ada", frozenset({("crm", "1")}), frozenset({"crm"}))

    with pytest.raises(ValueError, match="out-of-scope"):
        evaluate_retrieval_detailed([allowed, forbidden], [case])


def test_empty_detailed_evaluation_preserves_defined_zeros() -> None:
    summary, details = evaluate_retrieval_detailed([], [])
    assert details == []
    assert summary["cases"] == 0
    assert summary["judged_cases"] == 0
    assert summary["zero_result_rate"] == 0.0
