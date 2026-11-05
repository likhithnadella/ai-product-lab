# Client 01: bounded conversation pilot

**Status:** deterministic local simulation. Not an LLM-powered or deployed customer agent.

## Why this vertical slice exists
The first milestone proves that a customer-facing workflow can distinguish a
proposed account action from an explicitly confirmed account action. Natural
language understanding is deliberately **out of scope** until authorization,
policy limits, and replay semantics have executable tests.

## Run
From repository root, with development dependencies installed:

```bash
python -m app.retention_conversation_demo
pytest -q tests/test_retention_conversation.py tests/test_retention_simulator.py
ruff check app/retention_conversation.py app/retention_conversation_demo.py tests/test_retention_conversation.py
```

Expected demonstration: first turn offers a credit but does not write; second
turn applies a synthetic credit; replay returns the same result with one
recorded outcome. This is an expected contract, not a claimed CI result.

## Trust boundaries
- The caller supplies a typed intent, not an unrestricted language-model tool invocation.
- A trusted caller must establish Actor identity and authorized accounts; these
  objects are **not** safe to construct from user or model claims in a real API.
- The policy engine independently enforces account eligibility and maximum credit.
- Cancellation and unknown intent route to human review; no cancellation write exists.
- The action simulator requires explicit confirmation and an idempotency key.
- Trace events are fixed labels; raw conversation, account identifiers and financial
  details are not recorded.
- In-memory idempotency is process-local; it is **not** durable, transactional or
  sufficient for multiple workers.

## Threat model and known gaps
Prompt injection cannot alter this controller's deterministic intent branch or
policy engine, but this does **not** constitute a prompt-injection defense for a
future LLM parser. A malicious upstream caller could forge Actor or confirmation;
production requires authenticated identity, authorization checks, durable
confirmation records, and a server-side workflow/session state machine. There is
no model, persistent database, tool sandbox, rate limiting, cancellation
integration, customer outcome study, or production deployment.

## Next milestone
Add a trusted session store with server-issued confirmation tokens bound to
tenant, account, amount, policy version and expiry; reject stale confirmation and
replay across sessions. Only then introduce a model as an **untrusted proposal
generator**, with a versioned evaluation corpus and human escalation.
