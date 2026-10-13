"""Deterministic, permission-scoped lexical retrieval over canonical records."""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from app.models import IntakeRecord

_TOKEN = re.compile(r"\w+", re.UNICODE)
_FIELD_WEIGHTS = (("email", 4), ("first_name", 3), ("last_name", 3), ("company", 2))
_MAX_QUERY_LENGTH = 256
_MAX_QUERY_TERMS = 16


@dataclass(frozen=True)
class SearchHit:
    record: IntakeRecord
    score: int
    matched_fields: tuple[str, ...] = ()


def _fold(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    return "".join(char for char in normalized if not unicodedata.combining(char)).casefold()


def _terms(value: str | None) -> set[str]:
    return set(_TOKEN.findall(_fold(value)))


def _validate_query(query: str) -> set[str]:
    if len(query) > _MAX_QUERY_LENGTH:
        raise ValueError("query exceeds 256 characters")
    terms = _terms(query)
    if len(terms) > _MAX_QUERY_TERMS:
        raise ValueError("query exceeds 16 distinct terms")
    return terms


def search_records(
    records: Iterable[IntakeRecord],
    query: str,
    *,
    allowed_sources: frozenset[str],
    limit: int = 10,
    offset: int = 0,
) -> list[SearchHit]:
    """Rank scoped records without exposing an unauthenticated search endpoint.

    Callers must obtain allowed_sources from a trusted permission decision.
    Source filtering alone is not tenant or record-level authorization.
    """
    if not isinstance(allowed_sources, frozenset):
        raise TypeError("allowed_sources must be a frozenset from trusted authorization")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if not 0 <= offset <= 10000:
        raise ValueError("offset must be between 0 and 10000")

    query_terms = _validate_query(query)
    if not query_terms or not allowed_sources:
        return []

    folded_query = _fold(query.strip())
    # Only a phone-shaped query can bypass lexical term matching. Mixed
    # letters and digits must never become an accidental phone lookup.
    phone_query = re.sub(r"[\\s()+.\\-]", "", query)
    query_digits = phone_query if phone_query.isascii() and phone_query.isdecimal() else ""
    phone_lookup = len(query_digits) >= 7

    # Source identity is the ingestion key; repeated identical keys must not
    # appear twice in a search page. Last supplied record is authoritative.
    unique: dict[tuple[str, str], IntakeRecord] = {}
    for record in records:
        if record.source in allowed_sources and record.external_id:
            unique[(record.source, record.external_id)] = record

    hits: list[SearchHit] = []
    for record in unique.values():
        fields = [(_terms(getattr(record, name)), weight, name) for name, weight in _FIELD_WEIGHTS]
        scores = [
            max((weight for terms, weight, _ in fields if term in terms), default=0)
            for term in query_terms
        ]
        phone_match = bool(phone_lookup and record.phone and record.phone.endswith(query_digits))
        if any(score == 0 for score in scores) and not phone_match:
            continue

        matched = tuple(
            name for terms, _, name in fields if query_terms.intersection(terms)
        )
        score = sum(scores)
        if record.email and folded_query == _fold(record.email):
            score += 20
        if phone_match:
            score += 15
            matched += ("phone",)
        if any(
            folded_query == _fold(getattr(record, name))
            for name in ("first_name", "last_name", "company")
            if getattr(record, name)
        ):
            score += 5
        hits.append(SearchHit(record=record, score=score, matched_fields=matched))

    hits.sort(key=lambda hit: (-hit.score, hit.record.source, hit.record.external_id or ""))
    return hits[offset : offset + limit]
