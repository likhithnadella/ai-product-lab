"""Reproducible offline lexical retrieval benchmark; no external services required."""

import argparse
import json

from evals.judged_retrieval_fixture import CASES, RECORDS, VERSION
from evals.retrieval import evaluate_retrieval_detailed


def run(k: int = 5) -> dict[str, object]:
    metrics, diagnostics = evaluate_retrieval_detailed(RECORDS, CASES, k=k)
    return {
        "fixture_version": VERSION,
        "k": k,
        "metrics": metrics,
        "failures": [
            {
                "case_index": index,
                "query": diagnostic.query,
                "scope": diagnostic.allowed_sources,
                "missed_keys": diagnostic.missed_keys,
                "unexpected_keys": diagnostic.unexpected_keys,
            }
            for index, diagnostic in enumerate(diagnostics)
            if diagnostic.missed_keys or diagnostic.unexpected_keys
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(run(k=args.k), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
