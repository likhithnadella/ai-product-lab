# Session-bound synthetic confirmation pilot

The first deterministic retention controller accepted a caller-supplied boolean
`confirmed`. This pilot adds a **server-held pending offer** and one-shot
confirmation, reducing the risk that a model-proposed action can be mistaken for
user approval. It remains an educational, local-only simulation.

## Run

```bash
python -m app.retention_sessions_demo
python -m pytest tests/test_retention_sessions.py
```

## Trust boundary

A trusted application must authenticate the human, derive the `Actor` and
`session_id` from its own session management, and never accept those fields
from a language model or untrusted user message. The random offer handle is
not an authentication credential. A confirmation requires a matching session,
tenant, account, authorized actor, and an explicit `accept` decision. The
simulator rechecks current eligibility and authorization before the action.

The controller stores only a synthetic pending amount and scope metadata; no
raw dialogue or personal customer records. Decline invalidates the offer.
Accepted offers are consumed once; replays cannot create another credit.

## Limits and next steps

- Pending offers and simulated writes are in memory, not durable across
  processes or restarts.
- No expiration, revocation endpoint, concurrency lock, or atomic persistence.
  Concurrent confirmations could race; do **not** expose this as a web service.
- No authentication, CSRF protection, account ownership verification, or
  independent consent proof is implemented here.
- A real deployment needs server-side session authentication, short-lived
  expiring offers, persistent transactional compare-and-swap consumption,
  durable idempotency, audit records and retry/recovery semantics.
- The demo does not use an LLM, external billing service or real subscriber data.
- Success on synthetic tests cannot demonstrate production security or retention lift.

## Design decision

The deterministic policy engine remains the final authority. A future model
may interpret intent and explain policy but cannot authorize or execute a
transaction directly. The session layer is deliberately separate from the
existing `resolve` API so existing offline evaluation fixtures remain stable.
