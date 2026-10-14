"""Regression tests for retrieval metrics on negative and permission-scoped queries.

Negative queries should not inflate ranking metrics: they instead expose
false-positive results, a distinct failure mode for downstream AI context.
"""

import pytest

from app.models import IntakeRecord
from app.search import search_records
from evals.retrieval import RetrievalCase, evaluate_retrieval


def test_negative_queries_have_no_false_positives() -> None:
    records = [
        IntakeRecord(source="crm", external_id="1", first_name="Ada", last_name="Lovelace"),
        IntakeRecord(source="import", external_id="2", first_name="Grace", last_name="Hopper"),
    ]
    cases = [
        RetrievalCase(query="not-present", relevant_keys=frozenset(), allowed_sources=frozenset({"crm"})),
        RetrievalCase(query="Grace", relevant_keys=frozenset(), allowed_sources=frozenset({"crm"})),
    ]
    assert all(
        not search_records(records, case.query, allowed_sources=case.allowed_sources)
        for case in cases
    )
    metrics = evaluate_retrieval(records, cases)
    assert metrics["cases"] == 2
    assert metrics["judged_cases"] == 0
    assert metrics["zero_result_rate"] == 1.0


def test_positive_retrieval_respects_scope() -> None:
    records = [
        IntakeRecord(source="crm", external_id="1", first_name="Ada"),
        IntakeRecord(source="import", external_id="2", first_name="Ada"),
    ]
    hits = search_records(records, "Ada", allowed_sources=frozenset({"crm"}))
    assert [(hit.record.source, hit.record.external_id) for hit in hits] == [("crm", "1")]

    cases = [
        RetrievalCase(
            query="Ada",
            relevant_keys=frozenset({("crm", "1")}),
            allowed_sources=frozenset({"crm"}),
        )
    ]
    metrics = evaluate_retrieval(records, cases, k=1)
    assert metrics["recall_at_k"] == 1.0
    assert metrics["precision_at_k"] == 1.0
    assert metrics["mrr_at_k"] == 1.0


def test_relevance_judgments_outside_allowed_sources_are_rejected() -> None:
    records = [IntakeRecord(source="import", external_id="2", first_name="Ada")]
    cases = [
        RetrievalCase(
            query="Ada",
            relevant_keys=frozenset({("import", "2")}),
            allowed_sources=frozenset({"crm"}),
        )
    ]
    with pytest.raises(ValueError, match="allowed source scope"):
        evaluate_retrieval(records, cases)
