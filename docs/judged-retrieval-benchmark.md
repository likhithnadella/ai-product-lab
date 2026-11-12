# Judged lexical retrieval benchmark (issue #9)

This versioned offline benchmark uses **25 synthetic queries** and **8 synthetic records** across CRM, ERP and support sources. It covers duplicate identities across sources, full names, email, phone, organization matches, missing fields, no-result queries and restricted source scopes.

## Run

```bash
python -m evals.run_judged_retrieval --k 5
python -m pytest tests/test_judged_retrieval.py -q
ruff check evals/judged_retrieval_fixture.py evals/run_judged_retrieval.py tests/test_judged_retrieval.py
```

The CLI emits fixture version, query count, judged-case count, Recall@K, Precision@K, MRR@K, zero-result rate, negative-case false-positive rate and per-case failures. A failed expectation is visible; do not silently discard it.

## Relevance policy

Judgments are written independently of ranking scores. Record keys are (source, external_id), not human names: matching names in distinct sources may be distinct relevant records. Negative cases include intentionally empty allowed scopes and queries where a matching record exists in a different source. Scope is supplied as a trusted **offline fixture**, not evidence of authentication.

## Interpretation and limitations

These are hand-authored synthetic cases, not representative production traffic, not real users, and not proof of retrieval quality for a deployed service. Precision@K uses a fixed K denominator; empty-result negative cases are excluded from positive-query Recall/Precision/MRR and reported separately. Query-level diagnostics may contain synthetic query strings and must **not** be used to log real customer queries. This benchmark does not replace tenant-level authorization or validate the unauthenticated API. No external API keys, customer data or live systems are needed.

Future work: stratified larger independent judgments, explicit permission ownership, adversarial and multilingual cases, measured confidence intervals, and a baseline-vs-candidate comparison on a frozen test set.
