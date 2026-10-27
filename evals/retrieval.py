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
    if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= 100:
        raise ValueError("k must be between 1 and 100")

    keys = [(record.source, record.external_id) for record in records]
    if len(keys) != len(set(keys)):
        raise ValueError("evaluation records contain duplicate source identities")
    available_keys = set(keys)

    recall_sum = reciprocal_rank_sum = precision_sum = 0.0
    judged = zero_results = negative_cases = false_positive_cases = 0
    for case in cases:
        if any(source not in case.allowed_sources for source, _ in case.relevant_keys):
            raise ValueError("relevance judgments must respect the allowed source scope")
        if not case.relevant_keys <= available_keys:
            raise ValueError("relevance judgments reference unknown record identities")
        hits = search_records(records, case.query, allowed_sources=case.allowed_sources, limit=k)
        found = [(hit.record.source, hit.record.external_id) for hit in hits]
        # The evaluator must not silently award quality credit to a retrieval
        # implementation that violates scope, identity, or page-size contracts.
        if len(found) > k:
            raise ValueError("retrieval returned more than k hits")
        if any(source not in case.allowed_sources for source, _ in found):
            raise ValueError("retrieval returned out-of-scope record")
        if any(key not in available_keys for key in found):
            raise ValueError("retrieval returned unknown record identity")
        if len(found) != len(set(found)):
            raise ValueError("retrieval returned duplicate record identities")
        if not found:
            zero_results += 1
        if not case.relevant_keys:
            negative_cases += 1
            if found:
                false_positive_cases += 1
            continue

        judged += 1
        relevant_found = len(case.relevant_keys.intersection(found))
        recall_sum += relevant_found / len(case.relevant_keys)
        precision_sum += relevant_found / k
        for rank, key in enumerate(found, start=1):
            if key in case.relevant_keys:
                reciprocal_rank_sum += 1 / rank
                break

    return {
        "cases": len(cases),
        "judged_cases": judged,
        "recall_at_k": recall_sum / judged if judged else 0.0,
        "precision_at_k": precision_sum / judged if judged else 0.0,
        "mrr_at_k": reciprocal_rank_sum / judged if judged else 0.0,
        "zero_result_rate": zero_results / len(cases) if cases else 0.0,
        "negative_cases": negative_cases,
        "false_positive_rate_on_negatives": (
            false_positive_cases / negative_cases if negative_cases else 0.0
        ),
    }
