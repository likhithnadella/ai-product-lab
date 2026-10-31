"""Adversarial fixture integrity tests using synthetic-only identities."""

import pytest

from app.models import IntakeRecord
from evals.retrieval import RetrievalCase, evaluate_retrieval

RECORDS = [IntakeRecord(source="crm", external_id="synthetic-1", first_name="Ada")]


def case(query="Ada", *, scope=frozenset({"crm"}), keys=frozenset({("crm", "synthetic-1")})):
    return RetrievalCase(query, keys, scope)


def test_duplicate_query_and_scope_cannot_inflate_judged_sample() -> None:
    with pytest.raises(ValueError, match="duplicate query and source scope"):
        evaluate_retrieval(RECORDS, [case(), case()])


def test_same_query_with_distinct_permission_scopes_is_valid() -> None:
    reports = evaluate_retrieval(
        RECORDS,
        [case(), case(scope=frozenset({"partner"}), keys=frozenset())],
    )
    assert reports["cases"] == 2
    assert reports["judged_cases"] == 1
    assert reports["negative_cases"] == 1


@pytest.mark.parametrize("query", ["", "  ", "\t"])
def test_blank_queries_cannot_be_counted_as_negative_judgments(query: str) -> None:
    with pytest.raises(ValueError, match="nonblank"):
        evaluate_retrieval(RECORDS, [case(query, keys=frozenset())])


def test_empty_permission_scope_is_valid_security_negative() -> None:
    # No access must yield no hits, and remains a useful authorization regression.
    report = evaluate_retrieval(RECORDS, [case(scope=frozenset(), keys=frozenset())])
    assert report["negative_cases"] == 1
    assert report["zero_result_rate"] == 1.0
    assert report["false_positive_rate_on_negatives"] == 0.0


@pytest.mark.parametrize("source", ["", "  ", " crm "])
def test_invalid_permission_scope_is_rejected(source: str) -> None:
    with pytest.raises(ValueError, match="source scope"):
        evaluate_retrieval(RECORDS, [case(scope=frozenset({source}), keys=frozenset())])


@pytest.mark.parametrize("record", [
    IntakeRecord(source="", external_id="1"),
    IntakeRecord(source="crm", external_id=None),
    IntakeRecord(source="crm", external_id=" "),
])
def test_evaluation_requires_durable_record_identities(record: IntakeRecord) -> None:
    with pytest.raises(ValueError, match="nonblank"):
        evaluate_retrieval([record], [])
