"""Regression guards for hand-judged retrieval fixture integrity and scope."""

import pytest

from app.models import IntakeRecord
from app.search import search_records
from evals.judged_fixtures import CASES, RECORDS, judged_report
from evals.retrieval import RetrievalCase, evaluate_retrieval


def test_judged_fixture_references_only_existing_records() -> None:
    keys = {(record.source, record.external_id) for record in RECORDS}
    assert len(keys) == len(RECORDS), "duplicate record identities make judgments ambiguous"
    assert CASES, "empty benchmark would conceal ranking regressions"
    for case in CASES:
        assert case.relevant_keys <= keys
        assert all(source in case.allowed_sources for source, _ in case.relevant_keys)


def test_source_scope_does_not_leak_other_sources() -> None:
    for case in CASES:
        hits = search_records(RECORDS, case.query, allowed_sources=case.allowed_sources)
        assert all(hit.record.source in case.allowed_sources for hit in hits)


def test_evaluator_rejects_cross_scope_judgment() -> None:
    records = [IntakeRecord(source="crm", external_id="c1", first_name="Ada")]
    case = RetrievalCase("Ada", frozenset({("crm", "c1")}), frozenset({"partner"}))
    with pytest.raises(ValueError, match="allowed source scope"):
        evaluate_retrieval(records, [case])


def test_judged_report_is_reproducible_and_bounded() -> None:
    first = judged_report()
    assert first == judged_report()
    assert first["cases"] == len(CASES)
    assert first["judged_cases"] == sum(bool(case.relevant_keys) for case in CASES)
    for metric in ("recall_at_k", "precision_at_k", "mrr_at_k", "zero_result_rate"):
        assert 0 <= first[metric] <= 1
