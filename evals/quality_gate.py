"""Fail-closed quality policy for the versioned, synthetic retrieval benchmark.

This is a regression gate, not a claim about production retrieval performance.
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from math import isfinite


@dataclass(frozen=True)
class RetrievalGate:
    fixture_version: str = "2026-10-27.1"
    k: int = 5
    min_judged_cases: int = 14
    min_negative_cases: int = 5
    min_recall_at_k: float = 0.90
    min_precision_at_k: float = 0.20
    min_mrr_at_k: float = 0.90
    max_false_positive_rate_on_negatives: float = 0.0


DEFAULT_GATE = RetrievalGate()


def check_retrieval_gate(
    report: Mapping[str, object], gate: RetrievalGate = DEFAULT_GATE
) -> tuple[str, ...]:
    """Return deterministic failures; missing or invalid evidence never passes."""
    failures: list[str] = []
    if report.get("fixture_version") != gate.fixture_version:
        failures.append("fixture_version differs from the reviewed baseline")
    if type(report.get("k")) is not int or report["k"] != gate.k:
        failures.append("k differs from the reviewed cutoff")

    def count(name: str) -> int | None:
        value = report.get(name)
        if type(value) is not int or value < 0:
            failures.append(f"{name} must be a nonnegative integer")
            return None
        return value

    def rate(name: str) -> float | None:
        value = report.get(name)
        if type(value) not in (float, int) or not isfinite(value) or not 0 <= value <= 1:
            failures.append(f"{name} must be a finite rate between 0 and 1")
            return None
        return float(value)

    total = count("cases")
    judged = count("judged_cases")
    negative = count("negative_cases")
    if None not in (total, judged, negative) and total != judged + negative:
        failures.append("case cohorts do not sum to the reported total")
    if judged is not None and judged < gate.min_judged_cases:
        failures.append("judged_cases below minimum")
    if negative is not None and negative < gate.min_negative_cases:
        failures.append("negative_cases below minimum")

    recall = rate("recall_at_k")
    precision = rate("precision_at_k")
    mrr = rate("mrr_at_k")
    rate("zero_result_rate")
    false_positive = rate("false_positive_rate_on_negatives")
    if recall is not None and recall < gate.min_recall_at_k:
        failures.append("recall_at_k below minimum")
    if precision is not None and precision < gate.min_precision_at_k:
        failures.append("precision_at_k below minimum")
    if mrr is not None and mrr < gate.min_mrr_at_k:
        failures.append("mrr_at_k below minimum")
    if false_positive is not None and false_positive > gate.max_false_positive_rate_on_negatives:
        failures.append("false_positive_rate_on_negatives above maximum")
    return tuple(failures)


def gate_evidence(report: Mapping[str, object]) -> dict[str, object]:
    """Structured, machine-readable gate outcome for CI and local experiments."""
    violations = check_retrieval_gate(report)
    return {"passed": not violations, "violations": list(violations), "policy": asdict(DEFAULT_GATE)}
