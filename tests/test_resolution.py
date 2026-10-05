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
