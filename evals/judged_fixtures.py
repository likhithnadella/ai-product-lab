"""Versioned, hand-judged retrieval fixture for lexical search.

Relevance and permission scopes are written by hand, independent of the ranking
code, so ranking changes can be measured against them. The fixture is small and
synthetic: it is a regression set, not evidence of real-world search quality.
"""

from app.models import IntakeRecord
from evals.retrieval import RetrievalCase, evaluate_retrieval

FIXTURE_VERSION = "2026-10-14.1"

RECORDS = [
    IntakeRecord(source="crm", external_id="c1", first_name="Ada", last_name="Lovelace",
                 email="ada@analytical.io", company="Analytical Engines", phone="2145550101"),
    IntakeRecord(source="crm", external_id="c2", first_name="Grace", last_name="Hopper",
                 company="Navy"),
    IntakeRecord(source="crm", external_id="c3", first_name="Zoë", last_name="Müller",
                 email="zoe@berlin.example", company="Berlin Labs"),
    IntakeRecord(source="crm", external_id="c4", first_name="Kim", last_name="Park",
                 email="kim@corp.example"),
    IntakeRecord(source="import", external_id="i1", first_name="Ada", last_name="Lovelace",
                 email="ada@analytical.io", company="Analytical Engines"),
    IntakeRecord(source="partner", external_id="p1", first_name="Dev", last_name="Patel",
                 company="Sequoia", phone="4155550123"),
    IntakeRecord(source="partner", external_id="p2", first_name="Kim", last_name="Lee"),
    IntakeRecord(source="import", external_id="i2", first_name="Dev", last_name="Patel",
                 company="Sequoia", phone="4155550199"),
]

CASES = [
    RetrievalCase("Ada Lovelace", frozenset({("crm", "c1"), ("import", "i1")}),
                  frozenset({"crm", "import"})),
    RetrievalCase("Ada Lovelace", frozenset({("crm", "c1")}), frozenset({"crm"})),
    RetrievalCase("Zoe Muller", frozenset({("crm", "c3")}), frozenset({"crm"})),
    RetrievalCase("Dev Patel", frozenset({("partner", "p1")}), frozenset({"partner"})),
    RetrievalCase("ada@analytical.io", frozenset({("crm", "c1")}), frozenset({"crm"})),
    RetrievalCase("Kim", frozenset({("crm", "c4"), ("partner", "p2")}),
                  frozenset({"crm", "partner"})),
    RetrievalCase("Analytical", frozenset({("crm", "c1")}), frozenset({"crm"})),
    RetrievalCase("Grace Hopper", frozenset(), frozenset({"partner"})),
    RetrievalCase("missing person", frozenset(), frozenset({"crm", "import", "partner"})),
]


def judged_report(k: int = 5) -> dict[str, float | int | str]:
    report = evaluate_retrieval(RECORDS, CASES, k=k)
    return {"fixture_version": FIXTURE_VERSION, "k": k, **report}


if __name__ == "__main__":
    import json

    print(json.dumps(judged_report(), indent=2, sort_keys=True))
