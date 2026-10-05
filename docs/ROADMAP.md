# Product Roadmap

The lab builds one coherent product rather than disconnected demos. The product is a **Data Operations Copilot**: ingest messy business data, resolve identities safely, make it searchable, and layer AI only where it creates measurable value.

## Phase 1 — Trustworthy data foundation

- Canonical source-independent data contract
- Normalization and deterministic entity resolution
- Confidence thresholds and human-review queue
- Evaluation dataset: precision, recall, false-merge rate
- Batch ingestion and idempotency

## Phase 2 — Search that actually helps users

- Baseline lexical search and latency measurement
- Query rewriting for zero/weak-result queries
- Embeddings/vector retrieval experiment
- Hybrid retrieval and reranking
- Search evals: Recall@K, MRR/NDCG, latency, cost
- Preserve authorization filters throughout retrieval

## Phase 3 — AI assistance

- Provider abstraction and structured LLM outputs
- Grounded answers over retrieved records
- Citations/provenance and abstention
- Prompt/version management and regression evals
- Agent/tool use only for workflows where autonomy is justified

## Phase 4 — Production engineering

- Postgres persistence, migrations, repositories
- Background worker/queue for ingestion
- Caching, retries, rate limiting, circuit breakers
- OpenTelemetry-style traces, metrics, structured logs
- Threat model, secrets management, PII handling
- Docker and deployment architecture

## Phase 5 — Scale and product maturity

- Load tests at 10x traffic
- Horizontal scaling and backpressure exercises
- Cost-per-request and SLO dashboards
- Failure injection and recovery runbooks
- Frontend workflow for search, review, and explanations
- Architecture decision records and portfolio-ready system design

## Engineering principles

1. Measure a baseline before adding AI.
2. Prefer deterministic logic for deterministic problems.
3. Every AI feature gets an eval, fallback, and cost/latency budget.
4. Security filters happen before and during retrieval, never as an afterthought.
5. Optimize for user time saved, not demo impressiveness.
6. Each iteration should leave the system more observable and testable.
