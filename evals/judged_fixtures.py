"""Versioned, hand-judged retrieval fixture for lexical search.

Relevance and permission scopes are written by hand, independent of the ranking
code, so ranking changes can be measured against them. The fixture is small and
synthetic: it is a regression set, not evidence of real-world search quality.
"""

from dataclasses import asdict

from app.models import IntakeRecord
from evals.quality_gate import gate_evidence
from evals.retrieval import RetrievalCase, evaluate_retrieval, evaluate_retrieval_detailed

FIXTURE_VERSION = "2026-10-27.1"

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
    # Intentionally relevant-looking but outside the allowed source scope.
    RetrievalCase("Ada Lovelace", frozenset(), frozenset({"partner"})),
    # Additional hand-judged coverage for sparse records, phone suffixes,
    # source ambiguity, and a known lexical typo failure.
    RetrievalCase("Grace Hopper", frozenset({("crm", "c2")}), frozenset({"crm"})),
    RetrievalCase("Navy", frozenset({("crm", "c2")}), frozenset({"crm"})),
    RetrievalCase("5550123", frozenset({("partner", "p1")}), frozenset({"partner"})),
    RetrievalCase("4155550199", frozenset({("import", "i2")}), frozenset({"import"})),
    RetrievalCase("Kim", frozenset({("partner", "p2")}), frozenset({"partner"})),
    RetrievalCase("Dev Patel", frozenset({("partner", "p1"), ("import", "i2")}),
                  frozenset({"partner", "import"})),
    RetrievalCase("5550199", frozenset(), frozenset({"crm"})),
    RetrievalCase("absent@unknown.example", frozenset(),
                  frozenset({"crm", "import", "partner"})),
    RetrievalCase("Grace Hoper", frozenset({("crm", "c2")}), frozenset({"crm"})),
]


def judged_report(k: int = 5) -> dict[str, float | int | str]:
    report = evaluate_retrieval(RECORDS, CASES, k=k)
    return {"fixture_version": FIXTURE_VERSION, "k": k, **report}


def judged_detailed_report(k: int = 5) -> dict[str, object]:
    """Synthetic per-case failures alongside the stable aggregate report."""
    summary, cases = evaluate_retrieval_detailed(RECORDS, CASES, k=k)
    return {
        "summary": {"fixture_version": FIXTURE_VERSION, "k": k, **summary},
        "cases": [asdict(case) for case in cases],
    }


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Run the synthetic judged retrieval fixture")
    parser.add_argument("--k", type=int, default=5, help="ranking cutoff (1 to 100)")
    parser.add_argument("--details", action="store_true", help="include per-query failure evidence")
    parser.add_argument("--gate", action="store_true", help="enforce reviewed synthetic CI baseline")
    args = parser.parse_args()
    report = judged_detailed_report(args.k) if args.details else judged_report(args.k)
    outcome = gate_evidence(report["summary"] if args.details else report) if args.gate else None
    if outcome is not None:
        report["gate"] = outcome
    print(json.dumps(report, indent=2, sort_keys=True))
    if outcome is not None and not outcome["passed"]:
        raise SystemExit(1)
