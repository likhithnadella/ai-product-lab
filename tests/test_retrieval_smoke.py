from evals.retrieval_smoke import smoke_report


def test_synthetic_smoke_report() -> None:
    report = smoke_report()
    assert report["cases"] == 3
    assert report["judged_cases"] == 2
    assert report["recall_at_k"] == 1.0
    assert report["mrr_at_k"] == 1.0
    assert report["zero_result_rate"] == 1 / 3
