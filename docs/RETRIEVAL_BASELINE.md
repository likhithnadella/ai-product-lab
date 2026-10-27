# Establishing a retrieval baseline

Entity resolution answers whether two records refer to the same entity. Search answers a different question: which known records should a user see for a query? We need a measurable baseline before paying for embeddings or a language model.

The first implementation, `app/search.py`, scans a caller-provided record collection and scores exact case-folded word overlap in email, name, and company fields. Every query term must match somewhere. Field weights are explicit; an exact email receives an additional boost. Equal scores have a deterministic source/ID ordering. This is intentionally a small, inspectable baseline, not a search service.

**Permission boundary:** callers must pass `allowed_sources` from a trusted authorization decision. The function filters before ranking, but a source is not necessarily a tenant and the code does not authenticate users or enforce record-level permissions. Consequently there is no public search endpoint yet. A real service must establish tenant identity, enforce record-level policies, and test for cross-tenant leaks before exposure.

`evals/retrieval.py` computes Recall@K, Precision@K (relevant hits divided by K), and MRR@K on queries with relevance judgments, plus zero-result rate over all cases. Unjudged cases are excluded from relevance denominators. Run `python -m evals.retrieval_smoke` for a tiny deterministic smoke report. Its perfect recall/MRR reflect deliberately easy synthetic examples, **not** measured product quality. The unit tests check metric arithmetic and retrieval behavior; they are **not** a representative quality benchmark. Relevance labels outside a case's permitted source scope are rejected rather than silently depressing metrics. Before selecting a search engine or embedding model, assemble synthetic but realistic queries with independently judged relevant records, including spelling variants, multi-field lookups, source restrictions, and hard negatives. Record baseline latency, dataset size, and retrieval quality.

This implementation is O(records × query terms) and does not support stemming, typo tolerance, ranking calibration, pagination, or incremental indexing. At meaningful dataset size, compare it with Postgres full-text search or an inverted index. Add semantic/hybrid retrieval only after measuring failure categories where lexical matching is inadequate. Keep permission filtering consistent across every retrieval path.


## Reproducible judged-query regression

Run `python -m evals.judged_fixtures` from the repository root. The versioned
`evals/judged_fixtures.py` dataset contains **19 synthetic cases**, including
14 positive judgments and 5 negative cases. Keep the fixture version, query
scopes, and hand-judged relevant identities stable when comparing changes;
review and version intentional edits to the benchmark.

Interpret the metrics separately:

- **Recall@K** is relevant identities found divided by judged relevant identities,
  averaged across positive cases. **Precision@K** divides relevant hits by
  the configured K, even when fewer than K results are returned.
- **MRR@K** is the reciprocal rank of the first relevant hit, averaged across
  positive cases. **Zero-result rate** includes positive and negative cases.
- **False-positive rate on negatives** is the fraction of negative cases with
  at least one returned result. It is not a production false-positive estimate.
- Empty denominators produce zero rather than an undefined number; the report
  includes case counts so a zero score cannot masquerade as broad evidence.

## Evaluation integrity and fail-closed behavior

The evaluator validates both *judgments* and *retrieved results*. It rejects
duplicate input source identities, unknown relevance keys, and relevance keys
outside a case's permitted source scope. It also raises `ValueError` rather
than publishing potentially misleading metrics if a retrieval implementation
returns **out-of-scope results**, **identities absent from the evaluation
corpus**, **duplicate hit identities**, or **more than K hits**. Adversarial
tests inject these failures directly; ordinary lexical-search tests alone
would not establish that the evaluator catches future retrieval regressions.

These checks protect **offline evaluation integrity**, not runtime security.
They do not authenticate callers, derive tenant permissions, enforce per-record
authorization, or prove that the lexical baseline generalizes to customer data.
Do not enable public retrieval based on these tests. Review issue #8 before
exposing any search API, and expand issue #9's synthetic judgment coverage
before using metric changes to justify embeddings or a ranking migration.


## Query-level failure diagnostics (fixture v2026-10-27.1)

Run `python -m evals.judged_fixtures --details --k 5` to print the aggregate
metrics and each hand-judged query's permitted sources, expected identities,
retrieved identities in rank order, missed identities, unexpected identities,
and first relevant rank. Use `--k 3` to compare a different cutoff; the
aggregate-only command remains backward compatible. JSON output is stable
enough for local inspection, but it is not a versioned public API.

The expanded synthetic set adds sparse records, company-only queries, phone
suffix lookups, ambiguous names across sources, and scoped phone negatives.
It intentionally includes `Grace Hoper` with an expected `Grace Hopper`
identity. The current exact-token lexical baseline misses this typo; keeping
that failure visible is more informative than reporting perfect recall on an
easy fixture. At K=5, the hand-counted expectation is **13/14 positive queries
with a relevant result**, **16/70 macro Precision@5**, **6/19 zero-result
queries**, and **0/5 negative queries with a false positive**. CI tests
recalculate these values; the numbers are regression evidence on this fixture
only, not claims about users, customers, or search relevance in production.

Diagnostics use the same validation pass as aggregate scoring: an out-of-scope,
unknown, duplicate, or over-limit hit raises rather than publishing misleading
metrics. Query text and identities may contain sensitive data in real systems:
run this CLI **only on synthetic or explicitly approved sanitized evaluation
corpora**, and do not publish raw customer queries, names, or retrieved records
in CI artifacts, Slack, or logs. These diagnostics do not add runtime
authentication, tenant authorization, persistence, or performance guarantees.
