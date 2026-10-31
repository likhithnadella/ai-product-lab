"""Synthetic quality-gate regressions; no customer or personal data."""

from math import inf, nan

import pytest

from evals.judged_fixtures import judged_report
from evals.quality_gate import check_retrieval_gate, gate_evidence


def test_reviewed_synthetic_baseline_passes() -> None:
    report = judged_report(k=5)
    evidence = gate_evidence(report)
    assert evidence["passed"] is True
    assert evidence["violations"] == []
    assert evidence["policy"]["min_judged_cases"] == 14


@pytest.mark.parametrize(
    ("field", "value", "failure"),
    [
        ("fixture_version", "unreviewed-fixture", "fixture_version"),
        ("k", 1, "k differs"),
        ("judged_cases", 13, "judged_cases below"),
        ("negative_cases", 4, "negative_cases below"),
        ("recall_at_k", 0.89, "recall_at_k below"),
        ("precision_at_k", 0.19, "precision_at_k below"),
        ("mrr_at_k", 0.89, "mrr_at_k below"),
        ("false_positive_rate_on_negatives", 0.01, "above maximum"),
    ],
)
def test_gate_rejects_specific_regressions(field: str, value: object, failure: str) -> None:
    report = judged_report()
    report[field] = value
    assert any(failure in item for item in check_retrieval_gate(report))


@pytest.mark.parametrize("invalid", [nan, inf, -inf, True, None, "0.9", -0.1, 1.1])
def test_gate_rejects_invalid_or_missing_metric_evidence(invalid: object) -> None:
    report = judged_report()
    report["recall_at_k"] = invalid
    assert any("recall_at_k must be" in item for item in check_retrieval_gate(report))
    report.pop("recall_at_k")
    assert any("recall_at_k must be" in item for item in check_retrieval_gate(report))


def test_gate_rejects_inconsistent_cohort_counts() -> None:
    report = judged_report()
    report["cases"] = 20
    assert "case cohorts do not sum to the reported total" in check_retrieval_gate(report)


@pytest.mark.parametrize("invalid", [True, 14.0, -1, "14", None])
def test_gate_requires_integer_sample_counts(invalid: object) -> None:
    report = judged_report()
    report["judged_cases"] = invalid
    assert any("judged_cases must be" in item for item in check_retrieval_gate(report))


def test_gate_never_passes_when_negative_evidence_is_missing() -> None:
    report = judged_report()
    report.pop("negative_cases")
    report.pop("false_positive_rate_on_negatives")
    failures = check_retrieval_gate(report)
    assert any("negative_cases must be" in item for item in failures)
    assert any("false_positive_rate_on_negatives must be" in item for item in failures)
