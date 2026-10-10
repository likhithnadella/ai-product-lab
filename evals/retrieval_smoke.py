"""Small synthetic smoke dataset, not a representative retrieval benchmark."""

from app.models import IntakeRecord
from evals.retrieval import RetrievalCase, evaluate_retrieval


def smoke_report() -> dict[str, float | int]:
    records = [
        IntakeRecord(source="crm", external_id="c1", first_name="Asha", last_name="Rao", company="Northstar"),
        IntakeRecord(source="crm", external_id="c2", first_name="Asha", last_name="Singh", company="Northstar"),
        IntakeRecord(source="partner", external_id="p1", first_name="Dev", last_name="Patel", company="Sequoia"),
    ]
    cases = [
        RetrievalCase("Asha Rao", frozenset({("crm", "c1")}), frozenset({"crm"})),
        RetrievalCase("Dev Sequoia", frozenset({("partner", "p1")}), frozenset({"partner"})),
        RetrievalCase("missing person", frozenset(), frozenset({"crm", "partner"})),
    ]
    return evaluate_retrieval(records, cases, k=2)


if __name__ == "__main__":
    import json

    print(json.dumps(smoke_report(), indent=2, sort_keys=True))
