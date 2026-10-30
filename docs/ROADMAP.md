# Engineering Roadmap

This roadmap is a sequence of engineering questions, not a shopping list of AI technologies.

The product starts as a small trusted-data service and grows toward an enterprise AI context and operations layer. A phase is useful only if it leaves behind working behavior, tests/evals, and evidence for the next architectural decision.

## 1. Can we trust the records?

**Problem:** data arrives incomplete, duplicated, and differently shaped across source systems.

Build the canonical contract, normalization, explainable entity resolution, confidence thresholds, and a review path for ambiguity. Keep ingestion idempotency separate from entity matching so retries are safe without pretending that source identity equals real-world identity.

**Evidence to leave behind:** behavioral tests plus precision, recall, false-merge/review measurements.

**Current state:** the local ingestion API, in-process atomic replay handling, and ambiguity-aware resolution exist. Persistence, tenant authorization, and representative matching evaluation are not established.

## 2. Can users find the right thing?

A trustworthy store is not useful if retrieval is poor.

An internal lexical baseline and a small versioned synthetic judged-query fixture now exist. It measures positive-query recall/precision/MRR and negative-query false-positive rate, including a source-scoped negative query. The fixture is too small and hand-selected to establish real-world retrieval quality. Expand representative judgments and record baseline results before changing ranking or adding embeddings. Measure quality and latency before adding embeddings. Add query rewriting, vector retrieval, hybrid search, and reranking only when experiments show where each technique helps.

**Evidence:** Recall@K, Precision@K, MRR/NDCG where appropriate, zero-result rate, false-positive rate on negative queries, p50/p95 latency, and cost. Reproduce the current synthetic baseline with `python -m evals.judged_fixtures`; its results are regression signals, not production performance claims. Authorization filters must survive every retrieval path. The current caller-supplied source scope is not tenant authorization; do not expose search publicly until that boundary exists.

**Current CI regression gate (synthetic only):** `python -m evals.judged_fixtures --gate` verifies the reviewed fixture version `2026-10-27.1` at cutoff K=5, at least 14 positive and 5 negative judgments, Recall@5 and MRR@5 >= 0.90, Precision@5 >= 0.20, and zero false positives on negative cases. It rejects missing, malformed, nonfinite, or inconsistent metric evidence and exits nonzero on a failure. Use `--details` to inspect individual synthetic misses; the default CLI output remains unchanged without `--gate`. The reviewed baseline measures 13/14 Recall@5 and MRR@5 and 16/70 Precision@5, not real-world performance. Thresholds are intentionally below that baseline to detect gross regressions; they are not a service-level objective. Changing fixture version, K, or thresholds requires an explicit reviewed rebaseline. This small fixture can still overfit, and the gate cannot prove retrieval security or generalization.

## 3. Can a model answer without inventing context?

Add a provider boundary and structured model outputs after retrieval has a benchmark.

Ground answers in retrieved records, preserve provenance, support abstention, and version prompts/model configuration. A model or prompt change should run against regression evals before it is considered an improvement.

**Evidence:** task-quality evals, groundedness/provenance checks, regression results, latency, and cost per useful request.

## 4. When should the system act?

Tool use is valuable when a workflow benefits from model reasoning; an agent is not the default architecture.

Introduce schema-validated tools, MCP where interoperability is useful, explicit permissions, idempotent actions, and human approval for high-impact operations. Add multi-step orchestration only after a single-model/tool workflow exposes a real limitation.

**Evidence:** task completion rate, tool-error rate, approval/escalation rate, token/cost budget, and recovery behavior.

## 5. What changes when this becomes a real service?

The current process-local store is a deliberately temporary implementation; move to Postgres with migrations and transaction boundaries after defining tenant ownership and access checks. Add background work when synchronous processing becomes inappropriate. Introduce caching, rate limits, retries/backoff, timeouts, circuit breakers, and dead-letter/replay behavior as failure modes demand them.

Instrument structured logs, traces, metrics, and SLOs. Threat-model PII, tenant isolation, prompt injection, tool permissions, secrets, and audit history.

Containerize and deploy the service; use infrastructure as code once there is infrastructure worth reproducing.

**Evidence:** deploy/recovery history, SLOs, security tests, operational dashboards, and documented incidents.

## 6. Can the architecture defend a scale claim?

Generate realistic synthetic workloads and establish a baseline. Increase records, concurrency, and traffic until something fails. Diagnose the bottleneck before changing the architecture.

Possible changes—workers, Redis, partitioning, Kafka/event streaming, dedicated vector infrastructure, horizontal scaling—are introduced only when measurements justify them.

**Evidence:** dataset size, requests/sec, p50/p95/p99 latency, error rate, queue depth/lag, retrieval quality, recovery time, and cost per 1,000 requests before and after each architectural change.

The target is not an arbitrary “millions of users” statement. It is a reproducible performance story.

## 7. Can someone actually use it?

Build the product workflow around the capabilities that survived the earlier phases: search, review, explanations, provenance, and controlled actions. A Next.js/TypeScript frontend is a likely fit, but the interface should follow the workflow rather than drive the architecture.

Measure user outcomes such as time saved, review burden, successful task completion, and adoption—not just model metrics.

## Cross-cutting practice

As the system evolves, the repository should accumulate architecture decision records, incident/postmortem exercises, benchmark reports, and concise explanations of tradeoffs. Those artifacts are part of the product: they show why the system changed and what evidence drove the decision.

### Rules for every phase

- Measure before optimizing.
- Prefer the simplest design that satisfies the current constraint.
- Do not use an LLM where deterministic software is more reliable.
- Do not trade away authorization or auditability for retrieval quality.
- Every AI feature needs an evaluation strategy and a failure path.
- Treat latency, cost, security, and operability as product requirements.
- Rewrite documentation when the design changes; do not append a changelog disguised as a README.
