# Pending-offer capacity and expiry (synthetic pilot)

The session-bound retention controller is **process-local** and deliberately not a production billing system.

## Why this change

Expiring an offer at confirmation time does not reclaim its memory if a customer never returns. A caller could continually request eligible offers, causing unbounded growth of the in-memory pending dictionary. This PR introduces a configurable positive-integer `max_pending_offers` (default 1,000), prunes expired offers when proposing a new offer, and fails closed with `offer_capacity_reached` when all slots remain occupied.

## Tradeoffs and behavior

- Capacity is **global per controller instance**, not per tenant or actor. A noisy tenant can deny offers to others; production requires per-tenant quotas, rate limits and abuse monitoring.
- Pruning is **lazy**, on the next eligible proposal, not background garbage collection. Expired entries may remain in memory during inactivity.
- Expired handles are removed under the existing process-local lock; concurrent proposals in one process cannot exceed the configured cap.
- A capacity denial never creates a handle or applies a credit; it routes to human review.
- Reclaiming an expired handle changes later confirmation from `offer_expired` to `offer_not_found`. Both are safe denials; external clients should not depend on this distinction.
- This does not provide durable idempotency, distributed locking, authentication, network rate limiting or cross-worker consistency. Never expose the simulator as a public billing endpoint.

## Reproduce

```bash
pip install -e ".[dev]"
ruff check app/retention_sessions.py tests/test_retention_capacity.py
pytest -q tests/test_retention_capacity.py tests/test_retention_expiry.py
```

The tests use invented accounts and a controlled monotonic clock. They verify denial at capacity, expired-offer reclamation, freed capacity after decline, invalid configuration and no writes on unauthorized proposals. These are **regression assertions**, not measured production throughput or retention outcomes.

## Next step

Persist offers with expiration and atomic consume semantics, enforce per-tenant quotas and trusted caller identity, then load-test multi-worker races and report actual measurements before any deployment claim.
