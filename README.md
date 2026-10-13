# AI Product Lab

A private engineering prototype built in reviewable increments: start with messy data, make it trustworthy, make it searchable, and only then give an AI permission to reason or act on it.

## The problem

Enterprise AI demos usually begin at the exciting part: connect a model to some documents, add a chat box, and call it RAG.

Real systems inherit a harder problem. The same customer can arrive from a CRM, a CSV import, an email workflow, and an internal API. Fields are incomplete, identifiers disagree, retries happen, and two records that look similar are not necessarily the same person. If that layer is unreliable, a better model only produces more convincing answers from bad context.

This project starts there.

The long-term product is a trusted context and operations layer between enterprise systems and AI workflows. It should be able to ingest records from multiple sources, reconcile identity without hiding uncertainty, retrieve the right authorized context, and eventually let models use tools without bypassing the controls expected of production software.

The interesting question is not “how much AI can fit into the architecture?” It is **where does AI earn its place?**

## The story so far

### Chapter 1 — establish trust before intelligence

The first slice defines a source-independent `IntakeRecord`, normalizes email and phone data, and resolves a new record against known candidates.

Matching is intentionally explainable. Strong identifiers carry more weight than fuzzy name similarity, and the resolver does not force every input into a match. It can return `matched`, `review`, or `new_record` with the evidence behind the score.

That gives the project something important before adding an LLM: a measurable baseline.

The entity-resolution eval harness tracks precision, recall, and review rate so a future semantic or model-assisted approach has to demonstrate that it is actually better—not merely newer.

### Chapter 2 — make retries boring

The next problem appears as soon as data starts moving between systems: delivery is not exactly once.

A CRM sync can retry. A batch can be replayed. The same external identifier can exist in two source systems. Treating all of those cases as entity-resolution problems would mix two different questions:

- **Ingestion identity:** have we already processed this source record?
- **Entity identity:** do two different source records represent the same real-world entity?

The ingestion layer therefore uses `(source, external_id)` as its stable key and reports each item as `created`, `updated`, `unchanged`, or `rejected`. Tests cover replay safety, updates, source isolation, invalid input, and mixed batches.

The store is still in memory on purpose. The current goal is to get the contract and failure semantics right before persistence makes those decisions harder to change. Postgres, migrations, and transaction boundaries come after the behavior is understood.

## What exists today

```text
External systems
      |
      v
  Ingestion ---------> replay / validation semantics
      |
      v
Canonical records
      |
      v
Entity resolution ---> confidence + evidence ---> human review when uncertain
      |
      v
Trusted entities
      |
      +----> permission-scoped lexical retrieval (internal baseline)
      +----> grounded AI context         (later)
      +----> controlled tools / actions  (later)

Cross-cutting as the system grows:
evals | authorization | observability | reliability | latency | cost
```

The repository currently contains:

- a local FastAPI service with `/health`, `/v1/resolve`, and `/v1/ingest`
- Pydantic contracts for canonical records and resolution responses
- email and phone normalization
- deterministic + fuzzy entity matching with explainable evidence
- confidence-based human-review routing, including close-score ambiguity checks
- replay-safe batch ingestion with in-process atomic classification and writes (not cross-worker durable transactions)
- internal permission-scoped lexical search with synthetic quality metrics; no public search endpoint or tenant authorization
- entity-resolution evals
- pytest coverage for matching and ingestion behavior
- Ruff + pytest in GitHub Actions

See [the roadmap](docs/ROADMAP.md) for how this grows from a small trustworthy core into a production-style AI system.

## Why the architecture is deliberately small

This repo is meant to demonstrate engineering judgment, not the number of infrastructure logos that can fit in a diagram.

There is no Kafka yet because there is no measured throughput problem that requires Kafka. There is no dedicated vector database because the existing lexical baseline has not yet been evaluated on a representative judged-query set. There is no agent because the product does not yet have a workflow where autonomy beats deterministic software.

Complexity has to earn its way into the system.

As the project grows, changes should be backed by evidence: retrieval quality, p95/p99 latency, error rate, throughput, review rate, cost per request, or a concrete reliability/security requirement. The eventual scale exercises will deliberately create bottlenecks, measure them, change the architecture, and measure again.

## Where this is going

The build proceeds roughly in this order:

**trustworthy data → persistence → search baseline → hybrid retrieval/RAG → grounded model integration → eval gates → controlled tools/MCP → product UI → security/observability → deployment → load and failure testing**

That sequence is intentional. Each layer should create a baseline that the next layer has to beat.

At maturity, the repo should be able to answer engineering questions with evidence:

- How do we prevent stale or unauthorized context from reaching a model?
- When does semantic retrieval outperform lexical search, and at what cost?
- What happens when an upstream source replays two million events?
- How do prompt/model changes pass regression evaluation before release?
- What happens when the model provider is slow or unavailable?
- Where does the system bottleneck at 10x load?
- Which actions require human approval, and how is that enforced?
- What does one useful AI request cost?

The goal is not to claim “enterprise scale” because an architecture diagram says so. The goal is to produce measurements and failure history that make the claim defensible.

## Run it locally

Python 3.11+ is required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The generated API documentation is available at `http://127.0.0.1:8000/docs`.

Run the same basic quality gates used by CI:

```bash
ruff check .
pytest -q
```

## Repository map

```text
app/
  main.py          API boundary
  models.py        canonical request/response contracts
  ingestion.py     replay-safe ingestion semantics
  resolution.py    explainable entity matching and ambiguity routing
  search.py        internal lexical retrieval with caller-provided source scope

evals/
  entity_resolution.py   matching metrics
  retrieval.py           lexical retrieval metrics

tests/             behavioral and evaluation tests
docs/ROADMAP.md    product and engineering roadmap
.github/           CI
```

## Engineering principles

1. Start with the user/data failure, not a preferred technology.
2. Prefer deterministic software when the problem is deterministic.
3. Measure a baseline before claiming an AI improvement.
4. Expose uncertainty instead of manufacturing confidence.
5. Keep ingestion identity separate from real-world entity identity.
6. Every AI feature eventually needs an eval, fallback, and latency/cost budget.
7. Authorization belongs in the retrieval and tool path, not in a prompt.
8. Add infrastructure when a measured constraint justifies it.
9. Document not only what changed, but why the previous design stopped being enough.

## Current status

**Phase 1 — local data and retrieval prototype.**

The local API already exposes ingestion; entity matching now sends close-scoring candidates to review. Ingestion is replay-safe within one process, but state disappears on restart and the API has no caller authentication or tenant isolation. Do not expose it to untrusted networks. Internal lexical search is available as a baseline, not as an authorized API; its synthetic smoke evaluation is not evidence of real-world search quality. The immediate work is tenant/caller authorization, durable storage and a judged retrieval fixture before deploying or adding model-driven search. See [tenant isolation](https://github.com/likhithnadella/ai-product-lab/issues/8) and [retrieval evaluation](https://github.com/likhithnadella/ai-product-lab/issues/9).
