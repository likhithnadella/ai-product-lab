"""Offline evaluation of the lexical retrieval baseline."""

from dataclasses import dataclass

from app.models import IntakeRecord
from app.search import search_records

RecordKey = tuple[str, str]


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    relevant_keys: frozenset[RecordKey]
    allowed_sources: frozenset[str]


def evaluate_retrieval(
    records: list[IntakeRecord],
    cases: list[RetrievalCase],
    *,
    k: int = 5,
) -> dict[str, float | int]:
    """Recall@K and MRR@K for judged queries; zero-result rate for all cases."""
    if not 1 <= k <= 100:
        raise ValueError("k must be between 1 and 100")

    recall_sum = reciprocal_rank_sum = 0.0
    judged = zero_results = 0
    for case in cases:
        if any(source not in case.allowed_sources for source, _ in case.relevant_keys):
            raise ValueError("relevance judgments must respect the allowed source scope")
        hits = search_records(records, case.query, allowed_sources=case.allowed_sources, limit=k)
        found = [(hit.record.source, hit.record.external_id) for hit in hits]
        if not found:
            zero_results += 1
        if not case.relevant_keys:
            continue

        judged += 1
        recall_sum += len(case.relevant_keys.intersection(found)) / len(case.relevant_keys)
        for rank, key in enumerate(found, start=1):
            if key in case.relevant_keys:
                reciprocal_rank_sum += 1 / rank
                break

    return {
        "cases": len(cases),
        "judged_cases": judged,
        "recall_at_k": recall_sum / judged if judged else 0.0,
        "mrr_at_k": reciprocal_rank_sum / judged if judged else 0.0,
        "zero_result_rate": zero_results / len(cases) if cases else 0.0,
    }
