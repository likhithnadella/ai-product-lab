# Client 01 — Deterministic Retention Evaluation v1

**Scope:** Original synthetic subscription billing and retention policy simulator. No model inference, real customer data, deployed integration, real retention measurements or human-agent comparison.

## Reproduce

From the repository root, with development dependencies installed:

```bash
python -m evals.retention
pytest -q tests/test_retention_simulator.py tests/test_retention_evals.py
ruff check app/retention_simulator.py tests/test_retention_simulator.py evals/retention.py tests/test_retention_evals.py
```

The versioned corpus contains **24** independent synthetic scenarios: eligible credits, the $25 maximum, disputes above the monthly charge, inactive and unauthorized accounts, cross-tenant requests, missing confirmation, nonfinite money and invalid amounts. Each scenario executes the deterministic policy and simulated credit tool in a fresh in-memory store.

**Interpretation:** A passing test establishes agreement with the explicitly coded expectations, **not** that the policy is suitable for real subscribers. This is a contract regression baseline, not an LLM quality metric or an estimate of retention uplift. The suite does not measure latency, model cost, prompt-injection resilience, live integration failures, concurrent writes or durable idempotency.

## Engineering tradeoffs

- Fail closed on nonfinite charges, rather than allowing Python Decimal comparisons to raise on NaN.
- Reject whitespace-only idempotency keys, but preserve valid opaque keys exactly as supplied.
- Recheck authorization and confirmation even on an in-process replay.
- Keep this baseline separate from future agent-driven intent recognition. A future model may propose an action, but policy and authorization remain deterministic and independently enforced.

## Next iteration

Introduce a bounded conversation-state workflow with explicit confirmation and escalation; add adversarial user-message cases and synthetic tool failures; instrument measured task success and latency. Durable transactions and caller authentication are prerequisites for deployment, not properties of this simulator.
