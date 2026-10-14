import pytest

from app.search import search_records
from evals.judged_fixtures import CASES, FIXTURE_VERSION, RECORDS, judged_report


def test_report_reports_sample_size_and_fixture_version() -> None:
    report = judged_report(k=5)
    assert report["fixture_version"] == FIXTURE_VERSION
    assert report["cases"] == len(CASES) == 9
    assert report["judged_cases"] == 7
    assert report["zero_result_rate"] == pytest.approx(2 / 9)


def test_judged_metrics_match_hand_checked_values() -> None:
    report = judged_report(k=5)
    assert report["recall_at_k"] == 1.0
    assert report["mrr_at_k"] == 1.0
    # Each judged case contributes relevant_found / k; the sum is 1.8 over 7 cases.
    assert report["precision_at_k"] == pytest.approx(1.8 / 7)


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case.query}|{sorted(case.allowed_sources)}")
def test_hits_never_leave_the_case_scope(case) -> None:
    hits = search_records(RECORDS, case.query, allowed_sources=case.allowed_sources, limit=5)
    assert all(hit.record.source in case.allowed_sources for hit in hits)


def test_every_relevance_judgment_is_inside_its_scope() -> None:
    for case in CASES:
        assert all(source in case.allowed_sources for source, _ in case.relevant_keys)


def test_out_of_scope_duplicate_is_not_returned() -> None:
    # Both Ada records match "Ada Lovelace" equally; the import copy must stay hidden.
    hits = search_records(RECORDS, "Ada Lovelace", allowed_sources=frozenset({"crm"}))
    assert [(hit.record.source, hit.record.external_id) for hit in hits] == [("crm", "c1")]
