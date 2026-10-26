"""Adversarial regression tests for retrieval evaluation's trust boundaries.

All records and identities are synthetic. These tests inject broken search
results rather than relying on the current lexical implementation to leak.
"""

import pytest

from app.models import IntakeRecord
from app.search import SearchHit
from evals import retrieval
from evals.retrieval import RetrievalCase, evaluate_retrieval


def _record(source: str, external_id: str) -> IntakeRecord:
    return IntakeRecord(source=source, external_id=external_id, first_name="Ada")


@pytest.mark.parametrize("positive_case", [True, False])
def test_evaluator_rejects_out_of_scope_hits(monkeypatch, positive_case: bool) -> None:
    allowed = _record("crm", "1")
    forbidden = _record("partner", "2")
    case = RetrievalCase(
        "Ada",
        frozenset({("crm", "1")}) if positive_case else frozenset(),
        frozenset({"crm"}),
    )
    monkeypatch.setattr(
        retrieval, "search_records",
        lambda *args, **kwargs: [SearchHit(record=forbidden, score=10)],
    )

    with pytest.raises(ValueError, match="out-of-scope"):
        evaluate_retrieval([allowed, forbidden], [case])


@pytest.mark.parametrize("positive_case", [True, False])
def test_evaluator_rejects_unknown_hit_identity(monkeypatch, positive_case: bool) -> None:
    known = _record("crm", "1")
    unknown = _record("crm", "not-in-evaluation")
    case = RetrievalCase(
        "Ada",
        frozenset({("crm", "1")}) if positive_case else frozenset(),
        frozenset({"crm"}),
    )
    monkeypatch.setattr(
        retrieval, "search_records",
        lambda *args, **kwargs: [SearchHit(record=unknown, score=10)],
    )

    with pytest.raises(ValueError, match="unknown record identity"):
        evaluate_retrieval([known], [case])
