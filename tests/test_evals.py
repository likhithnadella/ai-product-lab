from app.models import IntakeRecord
from evals.entity_resolution import ResolutionCase, evaluate


def test_evaluation_reports_quality_and_review_load():
    cases = [
        ResolutionCase(
            name="strong-match",
            incoming=IntakeRecord(source="csv", email="a@example.com", phone="2145550100"),
            candidates=[
                IntakeRecord(
                    source="crm",
                    external_id="1",
                    email="a@example.com",
                    phone="2145550100",
                )
            ],
            expected_record_id="1",
        ),
        ResolutionCase(
            name="email-only-review",
            incoming=IntakeRecord(source="email", email="b@example.com"),
            candidates=[
                IntakeRecord(source="crm", external_id="2", email="b@example.com")
            ],
            expected_record_id="2",
        ),
        ResolutionCase(
            name="true-new-record",
            incoming=IntakeRecord(source="csv", first_name="New", last_name="Person"),
            candidates=[],
            expected_record_id=None,
        ),
    ]

    metrics = evaluate(cases)
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 0.5
    assert metrics["review_rate"] == 1 / 3
