import pytest

from app.models import IntakeRecord
from app.resolution import resolve, score_candidate


def test_normalization_and_exact_match():
    incoming = IntakeRecord(
        source="csv",
        email=" USER@Example.COM ",
        phone="+1 (214) 555-0100",
        first_name="Jon",
        last_name="Doe",
        company="Acme",
    )
    candidate = IntakeRecord(
        source="crm",
        external_id="lead-42",
        email="user@example.com",
        phone="2145550100",
        first_name="John",
        last_name="Doe",
        company="Acme Inc",
    )

    scored = score_candidate(incoming, candidate)
    assert scored.score >= 0.90
    assert "exact_email" in scored.reasons
    assert "exact_phone" in scored.reasons

    result = resolve(incoming, [candidate])
    assert result.decision == "matched"
    assert result.candidate.record_id == "lead-42"


def test_ambiguous_email_only_goes_to_review():
    incoming = IntakeRecord(source="email", email="same@example.com")
    candidate = IntakeRecord(source="crm", external_id="lead-1", email="same@example.com")

    result = resolve(incoming, [candidate])
    assert result.decision == "review"
    assert result.needs_review is True


def test_low_signal_becomes_new_record():
    incoming = IntakeRecord(source="csv", first_name="Alice", company="Northwind")
    candidate = IntakeRecord(
        source="crm", external_id="lead-2", first_name="Bob", company="Contoso"
    )

    result = resolve(incoming, [candidate])
    assert result.decision == "new_record"


def test_equal_strong_candidates_require_review():
    incoming = IntakeRecord(source="csv", email="same@example.com", phone="2145550100")
    candidates = [
        IntakeRecord(source="crm", external_id=key, email="same@example.com", phone="2145550100")
        for key in ("a", "b")
    ]
    result = resolve(incoming, candidates)
    assert result.decision == "review"
    assert result.needs_review is True


def test_near_tie_requires_review():
    incoming = IntakeRecord(
        source="csv", email="same@example.com", phone="2145550100", company="Acme"
    )
    candidates = [
        IntakeRecord(source="crm", external_id="a", email="same@example.com", phone="2145550100", company="Acme"),
        IntakeRecord(source="crm", external_id="b", email="same@example.com", phone="2145550100"),
    ]
    result = resolve(incoming, candidates)
    assert result.decision == "review"
    assert result.needs_review is True


def test_clear_winner_still_auto_matches():
    incoming = IntakeRecord(source="csv", email="same@example.com", phone="2145550100")
    candidates = [
        IntakeRecord(source="crm", external_id="a", email="same@example.com", phone="2145550100"),
        IntakeRecord(source="crm", external_id="b", email="other@example.com", phone="9999999999"),
    ]
    result = resolve(incoming, candidates)
    assert result.decision == "matched"
    assert result.candidate.record_id == "a"


def test_duplicate_source_identity_does_not_create_false_ambiguity():
    incoming = IntakeRecord(source="csv", email="same@example.com", phone="2145550100")
    candidate = IntakeRecord(source="crm", external_id="a", email="same@example.com", phone="2145550100")
    result = resolve(incoming, [candidate, candidate])
    assert result.decision == "matched"


def test_tied_review_candidate_is_stable_under_reordering():
    incoming = IntakeRecord(source="csv", email="same@example.com", phone="2145550100")
    first = IntakeRecord(source="crm", external_id="b", email="same@example.com", phone="2145550100")
    second = IntakeRecord(source="crm", external_id="a", email="same@example.com", phone="2145550100")
    forward = resolve(incoming, [first, second])
    reversed_result = resolve(incoming, [second, first])
    assert forward.decision == reversed_result.decision == "review"
    assert forward.candidate.record_id == reversed_result.candidate.record_id == "a"


@pytest.mark.parametrize(
    "settings",
    [
        {"review_threshold": -0.1},
        {"auto_match_threshold": 1.1},
        {"review_threshold": 0.9, "auto_match_threshold": 0.8},
        {"ambiguity_margin": -0.01},
        {"ambiguity_margin": 1.01},
    ],
)
def test_invalid_threshold_configuration_fails_even_without_candidates(settings: dict) -> None:
    incoming = IntakeRecord(source="crm")
    with pytest.raises(ValueError):
        resolve(incoming, [], **settings)
