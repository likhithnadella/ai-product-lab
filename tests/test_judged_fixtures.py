import json
import subprocess
import sys

import pytest

from app.search import search_records
from evals.judged_fixtures import (
    CASES,
    FIXTURE_VERSION,
    RECORDS,
    judged_detailed_report,
    judged_report,
)


def test_report_reports_sample_size_and_fixture_version() -> None:
    report = judged_report(k=5)
    assert report["fixture_version"] == FIXTURE_VERSION
    assert report["cases"] == len(CASES) == 19
    assert report["judged_cases"] == 14
    assert report["zero_result_rate"] == pytest.approx(6 / 19)
    assert report["negative_cases"] == 5


def test_judged_metrics_match_hand_checked_values() -> None:
    report = judged_report(k=5)
    assert report["recall_at_k"] == pytest.approx(13 / 14)
    assert report["mrr_at_k"] == pytest.approx(13 / 14)
    # 16 relevant hits over 14 positive cases at cutoff 5; one typo is missed.
    assert report["precision_at_k"] == pytest.approx(16 / (14 * 5))


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


def test_versioned_fixture_exposes_a_known_lexical_typo_failure() -> None:
    details = judged_detailed_report(k=5)
    assert details["summary"]["fixture_version"] == FIXTURE_VERSION
    assert len(details["cases"]) == 19
    missed = [case for case in details["cases"] if case["query"] == "Grace Hoper"]
    assert len(missed) == 1
    assert missed[0]["missed_keys"] == (("crm", "c2"),)
    assert missed[0]["retrieved_keys"] == ()


def test_phone_suffix_judgment_and_scope_negative() -> None:
    report = judged_detailed_report()
    by_query = {case["query"]: case for case in report["cases"]}
    assert by_query["5550123"]["retrieved_keys"] == (("partner", "p1"),)
    assert by_query["5550199"]["retrieved_keys"] == ()
    assert by_query["5550199"]["allowed_sources"] == ("crm",)


def test_judged_cli_can_emit_machine_readable_diagnostics() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.judged_fixtures", "--details", "--k", "3"],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    assert report["summary"]["k"] == 3
    assert report["summary"]["cases"] == 19
    assert len(report["cases"]) == 19
    assert report["cases"][-1]["query"] == "Grace Hoper"



def test_judged_cli_quality_gate_passes_and_reports_reviewed_policy() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.judged_fixtures", "--gate"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["gate"]["passed"] is True
    assert report["gate"]["violations"] == []
    assert report["gate"]["policy"]["k"] == 5


def test_judged_cli_quality_gate_fails_closed_on_unreviewed_cutoff() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.judged_fixtures", "--gate", "--details", "--k", "1"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    report = json.loads(result.stdout)
    assert report["gate"]["passed"] is False
    assert any("k differs" in reason for reason in report["gate"]["violations"])
    assert len(report["cases"]) == 19


def test_judged_cli_without_gate_keeps_its_existing_output_contract() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.judged_fixtures"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "gate" not in json.loads(result.stdout)
