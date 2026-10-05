# AI Product Lab

A production-minded **Data Operations Copilot** built end to end as a long-running learning and portfolio project.

The product starts with a real enterprise problem: teams receive messy customer/lead data from CSVs, email, CRMs, and other sources. Before adding an LLM, the system creates a trustworthy data layer: normalize records, resolve identities, expose uncertainty, and route ambiguous cases for review. Search, RAG, agents, evals, observability, security, and scaling are then added against a measurable baseline.

## Why this project

This repo is intentionally not a collection of AI demos. It is designed to exercise the judgment expected from AI product engineers, forward-deployed engineers, and technical founders: identify the actual bottleneck, choose the simplest useful architecture, measure it, ship it, and evolve it under real constraints.

## V0.1 — trustworthy data foundation

The first vertical slice is live in the repository:

- FastAPI service with `/health` and `/v1/resolve`
- Canonical `IntakeRecord` independent of source system
- Email and phone normalization
- Explainable deterministic + fuzzy entity matching
- Confidence-based `matched`, `review`, and `new_record` decisions
- Entity-resolution evaluation harness for precision, recall, and review rate
- Idempotent batch ingestion using `(source, external_id)` as the stable source identity
- Per-item ingestion outcomes: `created`, `updated`, `unchanged`, or `rejected`
- Tests for matching quality, replay safety, updates, source isolation, and invalid records
- GitHub Actions CI with Ruff + pytest

Two design decisions are deliberate. **Entity cleansing is not automatically an LLM problem**: deterministic signals create a cheap, explainable baseline that later AI components must beat. **Retries must be safe**: ingestion requires a stable source identity instead of guessing whether two anonymous records are the same person. Entity resolution and ingestion idempotency solve different problems and stay separate.

The current record store is intentionally in-memory. It defines and tests ingestion semantics before adding Postgres, migrations, and transaction behavior. The store boundary can later be replaced by a persistent repository without changing the batch contract.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Then open the generated API docs at `http://127.0.0.1:8000/docs`.

Run quality checks:

```bash
ruff check .
pytest -q
```

## Architecture direction

```text
Sources (CSV / Email / APIs)
          |
          v
   Ingestion adapters
          |
          v
Normalize -> Entity Resolution -> Review Queue
          |                    |
          +------> Store <-----+
                     |
             Search / Retrieval
              |             |
        lexical/hybrid    vector/RAG
              \             /
               AI assistance
                     |
              Product workflow

Cross-cutting: evals | auth | observability | cost | reliability
```

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the staged build plan.

## Learning targets

Python/FastAPI, data modeling and pipelines, search/query rewriting, embeddings and RAG, LLM integration and structured outputs, evals, agent/tool design, frontend product work, Postgres, queues/caching, CI/CD, security, observability, reliability, cost/latency optimization, and scaling/system design.

## Status

**Phase 1: Trustworthy data foundation — in progress.** Entity-resolution measurement and replay-safe batch ingestion now exist. Next: expose ingestion through an API boundary and introduce persistent storage only after the contract and failure semantics are stable.
