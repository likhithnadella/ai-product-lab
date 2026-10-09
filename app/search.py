"""Deterministic lexical retrieval over a caller-authorized record collection."""

from collections.abc import Iterable
from dataclasses import dataclass
import re

from app.models import IntakeRecord

_TOKEN = re.compile(r"\w+", re.UNICODE)
_FIELD_WEIGHTS = (("email", 4), ("first_name", 3), ("last_name", 3), ("company", 2))


@dataclass(frozen=True)
class SearchHit:
    record: IntakeRecord
    score: int


def _terms(value: str | None) -> set[str]:
    return set(_TOKEN.findall((value or "").casefold()))


def search_records(
    records: Iterable[IntakeRecord],
    query: str,
    *,
    allowed_sources: frozenset[str],
    limit: int = 10,
) -> list[SearchHit]:
    """Require all query terms and rank by explicit field weights.

    allowed_sources must come from trusted permissions, not request input.
    This internal function is not itself an authorization system.
    """
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")

    query_terms = _terms(query)
    if not query_terms or not allowed_sources:
        return []

    hits: list[SearchHit] = []
    for record in records:
        if record.source not in allowed_sources or not record.external_id:
            continue

        fields = [(_terms(getattr(record, name)), weight) for name, weight in _FIELD_WEIGHTS]
        scores = [
            max((weight for terms, weight in fields if term in terms), default=0)
            for term in query_terms
        ]
        if any(score == 0 for score in scores):
            continue

        score = sum(scores)
        if record.email and query.strip().casefold() == record.email:
            score += 20
        hits.append(SearchHit(record=record, score=score))

    hits.sort(key=lambda hit: (-hit.score, hit.record.source, hit.record.external_id or ""))
    return hits[:limit]
