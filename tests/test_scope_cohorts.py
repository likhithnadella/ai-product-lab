"""Synthetic cohort diagnostics protect against aggregate-only quality claims."""

import json
import subprocess
import sys
from dataclasses import replace

import pytest

from evals.judged_fixtures import CASES, RECORDS, judged_detailed_report
from evals.retrieval import RetrievalCase, RetrievalDiagnostic, evaluate_retrieval_detailed
from evals.scope_cohorts import scope_cohorts


def test_scope_breakdown_exposes_known_typo_miss() -> None:
    report = judged_detailed_report()
    by_scope = {tuple(row["allowed_sources"]): row for row in report["scope_cohorts"]}
    crm = by_scope[("crm",)]
    assert crm["positive_cases"] == 7
    assert crm["positive_hits"] == 6
    assert crm["positive_hit_rate"] == pytest.approx(6 / 7)
    assert crm["positive_recall_at_k"] == pytest.approx(6 / 7)
    assert crm["positive_mrr_at_k"] == pytest.approx(6 / 7)
    assert crm["negative_cases"] == 1
    assert crm["negative_false_positives"] == 0


def test_scope_breakdown_separates_negative_permission_cases() -> None:
    report = judged_detailed_report()
    partner = next(
        row for row in report["scope_cohorts"] if row["allowed_sources"] == ("partner",)
    )
    assert partner["positive_cases"] == 3
    assert partner["positive_hits"] == 3
    assert partner["negative_cases"] == 2
    assert partner["negative_false_positives"] == 0
    assert partner["negative_false_positive_rate"] == 0.0


def test_breakdown_is_consistent_with_overall_sample() -> None:
    report = judged_detailed_report()
    rows = report["scope_cohorts"]
    assert sum(row["positive_cases"] for row in rows) == report["summary"]["judged_cases"]
    assert sum(row["negative_cases"] for row in rows) == report["summary"]["negative_cases"]
    assert sum(row["positive_hits"] for row in rows) == 13
    assert len({tuple(row["allowed_sources"]) for row in rows}) == len(rows)


def test_scope_cohorts_rejects_mismatched_diagnostics() -> None:
    _, diagnostics = evaluate_retrieval_detailed(RECORDS, CASES)
    with pytest.raises(ValueError, match="same length"):
        scope_cohorts(CASES, diagnostics[:-1])
    altered = list(diagnostics)
    first = altered[0]
    altered[0] = RetrievalDiagnostic(
        query="different query",
        allowed_sources=first.allowed_sources,
        relevant_keys=first.relevant_keys,
        retrieved_keys=first.retrieved_keys,
        missed_keys=first.missed_keys,
        unexpected_keys=first.unexpected_keys,
        first_relevant_rank=first.first_relevant_rank,
    )
    with pytest.raises(ValueError, match="does not match"):
        scope_cohorts(CASES, altered)


def test_detailed_cli_exposes_scope_breakdown_without_changing_default() -> None:
    detailed = subprocess.run(
        [sys.executable, "-m", "evals.judged_fixtures", "--details"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(detailed.stdout)["scope_cohorts"]
    default = subprocess.run(
        [sys.executable, "-m", "evals.judged_fixtures"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "scope_cohorts" not in json.loads(default.stdout)


def test_scope_cohorts_rejects_forged_relevance_or_cross_scope_results() -> None:
    _, diagnostics = evaluate_retrieval_detailed(RECORDS, CASES)
    first = diagnostics[0]
    for forged in (
        replace(first, relevant_keys=()),
        replace(first, retrieved_keys=(("private", "synthetic-1"),)),
        replace(first, retrieved_keys=(first.retrieved_keys[0],) * 2),
    ):
        with pytest.raises(ValueError, match="inconsistent diagnostic"):
            scope_cohorts(CASES, [forged, *diagnostics[1:]])


def test_scope_cohorts_rejects_forged_misses_and_rank() -> None:
    _, diagnostics = evaluate_retrieval_detailed(RECORDS, CASES)
    first = diagnostics[0]
    for forged in (
        replace(first, missed_keys=first.relevant_keys),
        replace(first, unexpected_keys=first.retrieved_keys),
        replace(first, first_relevant_rank=4),
    ):
        with pytest.raises(ValueError, match="inconsistent diagnostic"):
            scope_cohorts(CASES, [forged, *diagnostics[1:]])


def test_partial_recall_is_not_misreported_as_full_scope_success() -> None:
    case = RetrievalCase("Asha", frozenset({("crm", "a"), ("crm", "b")}), frozenset({"crm"}))
    diagnostic = RetrievalDiagnostic(
        query="Asha",
        allowed_sources=("crm",),
        relevant_keys=(("crm", "a"), ("crm", "b")),
        retrieved_keys=(("crm", "a"),),
        missed_keys=(("crm", "b"),),
        unexpected_keys=(),
        first_relevant_rank=1,
    )
    cohort = scope_cohorts([case], [diagnostic])[0]
    assert cohort["positive_hit_rate"] == 1.0
    assert cohort["positive_recall_at_k"] == 0.5
    assert cohort["positive_mrr_at_k"] == 1.0


def test_compact_cohort_cli_retains_aggregate_gate_without_query_details() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.judged_fixtures", "--cohorts", "--gate"],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert set(payload) == {"summary", "scope_cohorts", "gate"}
    assert payload["gate"]["passed"] is True
    assert payload["summary"]["judged_cases"] == 14
    assert payload["scope_cohorts"]
    assert all("query" not in cohort for cohort in payload["scope_cohorts"])


def test_cohort_cli_and_per_query_details_are_mutually_exclusive() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.judged_fixtures", "--cohorts", "--details"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "not allowed with argument" in result.stderr
