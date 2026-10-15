from difflib import SequenceMatcher

from app.models import IntakeRecord, MatchCandidate, ResolutionResult


def _similarity(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left.casefold().strip(), right.casefold().strip()).ratio()


def score_candidate(incoming: IntakeRecord, candidate: IntakeRecord) -> MatchCandidate:
    """Deterministic first-pass matching; AI is intentionally not required here."""
    reasons: list[str] = []
    score = 0.0

    if incoming.email and incoming.email == candidate.email:
        score += 0.65
        reasons.append("exact_email")
    if incoming.phone and incoming.phone == candidate.phone:
        score += 0.25
        reasons.append("exact_phone")

    name_score = (
        _similarity(incoming.first_name, candidate.first_name)
        + _similarity(incoming.last_name, candidate.last_name)
    ) / 2
    if name_score >= 0.85:
        score += 0.07 * name_score
        reasons.append("fuzzy_name")

    company_score = _similarity(incoming.company, candidate.company)
    if company_score >= 0.85:
        score += 0.03 * company_score
        reasons.append("fuzzy_company")

    return MatchCandidate(
        record_id=candidate.external_id or "unknown",
        score=min(score, 1.0),
        reasons=reasons,
    )


def resolve(
    incoming: IntakeRecord,
    candidates: list[IntakeRecord],
    auto_match_threshold: float = 0.90,
    review_threshold: float = 0.65,
    ambiguity_margin: float = 0.05,
) -> ResolutionResult:
    if not candidates:
        return ResolutionResult(decision="new_record", confidence=1.0)

    # Replayed copies of one source record are not competing identities.
    # Anonymous candidates cannot be deduplicated safely.
    unique: dict[tuple[str, str], IntakeRecord] = {}
    anonymous: list[IntakeRecord] = []
    for candidate in candidates:
        if candidate.external_id:
            unique[(candidate.source, candidate.external_id)] = candidate
        else:
            anonymous.append(candidate)

    # Stable source/identity ordering makes ambiguous review choices reproducible.
    # Anonymous candidates have no durable identity; preserve their input order.
    named = sorted(unique.items(), key=lambda pair: pair[0])
    ordered = [record for _, record in named] + anonymous
    ranked = sorted(
        (score_candidate(incoming, candidate) for candidate in ordered),
        key=lambda item: item.score,
        reverse=True,
    )
    best = ranked[0]

    # An auto-match must be clearly better than the runner-up; otherwise
    # the correct outcome is review, never input-order-dependent merging.
    if (len(ranked) > 1 and best.score >= review_threshold
            and best.score - ranked[1].score < ambiguity_margin):
        return ResolutionResult(
            decision="review", confidence=best.score, candidate=best, needs_review=True
        )

    if best.score >= auto_match_threshold:
        return ResolutionResult(decision="matched", confidence=best.score, candidate=best)
    if best.score >= review_threshold:
        return ResolutionResult(
            decision="review", confidence=best.score, candidate=best, needs_review=True
        )
    return ResolutionResult(decision="new_record", confidence=1 - best.score, candidate=best)
