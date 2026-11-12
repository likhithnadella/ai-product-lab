"""Guard benchmark relevance, source isolation, and reproducibility."""

from evals.judged_retrieval_fixture import ALL, CASES, RECORDS, VERSION
from evals.retrieval import evaluate_retrieval_detailed
from evals.run_judged_retrieval import run


def test_judgments_are_versioned_and_well_formed() -> None:
    assert VERSION
    assert len(CASES) >= 20
    assert len(RECORDS) >= 8
    assert len({(record.source, record.external_id) for record in RECORDS}) == len(RECORDS)
    assert all(record.source in ALL for record in RECORDS)
    assert all(
        key[0] in case.allowed_sources
        for case in CASES
        for key in case.relevant_keys
    )


def test_benchmark_has_positive_negative_and_restricted_scope_cases() -> None:
    assert any(case.relevant_keys for case in CASES)
    assert any(not case.relevant_keys for case in CASES)
    assert any(case.allowed_sources != ALL for case in CASES)
    assert any(not case.allowed_sources for case in CASES)


def test_benchmark_is_deterministic_and_does_not_leak_scope() -> None:
    metrics, diagnostics = evaluate_retrieval_detailed(RECORDS, CASES, k=5)
    metrics_again, diagnostics_again = evaluate_retrieval_detailed(RECORDS, CASES, k=5)
    assert (metrics, diagnostics) == (metrics_again, diagnostics_again)
    assert metrics["cases"] == len(CASES)
    for case, diagnostic in zip(CASES, diagnostics, strict=True):
        assert all(source in case.allowed_sources for source, _ in diagnostic.retrieved_keys)
        assert len(diagnostic.retrieved_keys) <= 5


def test_cli_report_matches_evaluator() -> None:
    report = run(k=5)
    metrics, _ = evaluate_retrieval_detailed(RECORDS, CASES, k=5)
    assert report["fixture_version"] == VERSION
    assert report["metrics"] == metrics
    assert isinstance(report["failures"], list)
