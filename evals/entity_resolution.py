from dataclasses import dataclass

from app.models import IntakeRecord
from app.resolution import resolve


@dataclass(frozen=True)
class ResolutionCase:
    name: str
    incoming: IntakeRecord
    candidates: list[IntakeRecord]
    expected_record_id: str | None


def evaluate(cases: list[ResolutionCase]) -> dict[str, float | int]:
    """Measure auto-match quality without counting human-review cases as correct."""
    true_positive = false_positive = false_negative = review = 0

    for case in cases:
        result = resolve(case.incoming, case.candidates)
        predicted = result.candidate.record_id if result.decision == "matched" and result.candidate else None

        if result.decision == "review":
            review += 1
        if predicted and predicted == case.expected_record_id:
            true_positive += 1
        elif predicted and predicted != case.expected_record_id:
            false_positive += 1
        elif case.expected_record_id and not predicted:
            false_negative += 1

    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative
    total = len(cases)
    return {
        "cases": total,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "review": review,
        "precision": true_positive / precision_denominator if precision_denominator else 0.0,
        "recall": true_positive / recall_denominator if recall_denominator else 0.0,
        "review_rate": review / total if total else 0.0,
    }
