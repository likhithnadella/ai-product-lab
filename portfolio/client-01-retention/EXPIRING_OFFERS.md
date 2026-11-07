# Expiring session offers — engineering decision

**Scope:** synthetic local-only retention case study. No LLM, real account, customer data, API authentication, distributed storage or production service.

## Failure mode addressed
A previously proposed credit could remain valid indefinitely; concurrent confirmation calls could both pass the pending-offer lookup. The new controller stores a monotonic expiry deadline and serializes offer lookup, authorization, expiry, consumption and simulated action under a process-local reentrant lock.

## Security and correctness invariants
- A valid authenticated actor and server-owned session ID are assumed; neither is established by this module.
- The handle is randomly generated and is **not** an authentication credential.
- Account, tenant, actor permissions and session must match before consuming an offer.
- Expiry is checked after authorization and at the confirmation boundary; a request at the exact deadline is denied.
- Invalid TTL values, including NaN and infinity, fail at construction.
- A second sequential or simultaneous acceptance cannot cause another simulated write in the **same controller process**.
- Decline consumes the offer without applying a credit.

## Reproduce
From repository root with dev dependencies installed:

```bash
pytest -q tests/test_retention_sessions.py tests/test_retention_expiry.py
ruff check app/retention_sessions.py tests/test_retention_expiry.py
python -m app.retention_sessions_demo
```

## Tradeoffs and unresolved risks
The lock serializes all offers within one controller, reducing throughput but keeping the demonstration understandable. Pending entries remain in memory until confirmation or process shutdown; expired unused entries need scheduled cleanup and bounded capacity. Process restarts discard state. Multi-process workers do not share state or locks, so this is **not** distributed atomicity or durable idempotency. Clock injection supports deterministic tests but must not be exposed to an untrusted caller. No identity proof, rate limiting, session revocation, persistent transaction log, atomic database compare-and-swap, or production observability exists.

## Production direction
Use authenticated session middleware, a transactional datastore with conditional consume and TTL/cleanup, unique idempotency constraints, per-tenant limits and explicit account-change audit events. Test cross-worker races, restarts, expired handles and fault injection against that implementation. Evaluate actual success/latency/cost before claiming operational gains.
