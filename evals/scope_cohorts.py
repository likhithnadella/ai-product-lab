"""Offline, synthetic retrieval failure breakdown by trusted source scope.

These are fixture-level diagnostics, not user-traffic or production metrics.
"""

from collections import defaultdict

from evals.retrieval import RetrievalCase, RetrievalDiagnostic


def scope_cohorts(
    cases: list[RetrievalCase], diagnostics: list[RetrievalDiagnostic]
) -> list[dict[str, object]]:
    """Separate positive and negative query outcomes to reveal hidden regressions.

    A positive hit means *any* relevant record was found, not full recall.
    A negative false positive means *any* record was returned for a no-result
    judgment. Both denominators are per-scope, not global case counts.
    """
    if len(cases) != len(diagnostics):
        raise ValueError("cases and diagnostics must have the same length")

    groups: dict[tuple[str, ...], dict[str, int]] = defaultdict(
        lambda: {
            "positive_cases": 0,
            "positive_hits": 0,
            "negative_cases": 0,
            "negative_false_positives": 0,
        }
    )
    for case, diagnostic in zip(cases, diagnostics, strict=True):
        scope = tuple(sorted(case.allowed_sources))
        if scope != diagnostic.allowed_sources or case.query != diagnostic.query:
            raise ValueError("diagnostic does not match the corresponding judgment")
        counts = groups[scope]
        if case.relevant_keys:
            counts["positive_cases"] += 1
            counts["positive_hits"] += int(diagnostic.first_relevant_rank is not None)
        else:
            counts["negative_cases"] += 1
            counts["negative_false_positives"] += int(bool(diagnostic.retrieved_keys))

    return [
        {
            "allowed_sources": scope,
            **counts,
            "positive_hit_rate": (
                counts["positive_hits"] / counts["positive_cases"]
                if counts["positive_cases"] else None
            ),
            "negative_false_positive_rate": (
                counts["negative_false_positives"] / counts["negative_cases"]
                if counts["negative_cases"] else None
            ),
        }
        for scope, counts in sorted(groups.items())
    ]
