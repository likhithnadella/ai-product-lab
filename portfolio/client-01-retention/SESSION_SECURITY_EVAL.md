# Retention session boundary — synthetic security evaluation

This is a **deterministic local simulation**, not an authenticated service,
production billing integration, deployed AI agent, or empirical security audit.

## Reproduce

From the repository root with development dependencies installed:

```bash
python -m evals.retention_session_security
pytest -q tests/test_retention_session_security_eval.py
ruff check evals/retention_session_security.py tests/test_retention_session_security_eval.py
```

The CLI emits JSON with the number of scenarios, pass/fail counts, expected
versus observed reasons, and the count of simulated credit actions. A nonzero
exit code means at least one scenario failed. No random offer handles, session
identifiers or synthetic account identifiers are emitted in the report.

## Threats and evidence

Each case creates an isolated controller and synthetic account. Tests cover:
authorized acceptance and decline; wrong tenant, account or session; expiration;
one-shot replay; invalid decisions; tenant quota denial; rejection without
consuming an authorized offer; and expiration-based quota recovery.

The controlled clock makes expiry tests reproducible. The observed action count
is read from the local simulator ledger, not inferred from response text.

## Interpretation and limitations

Passing scenarios demonstrate these *specific code paths* under single-process
execution. They do not establish absence of vulnerabilities, concurrency safety
across workers, authorization of a caller's claimed Actor, persistence, rate
limits, durable idempotency, or security against a compromised host.

The controller uses an injected Actor and session ID; a real deployment must
bind these to authenticated server-side identity. Process-local locks and
memory cannot guarantee exactly-once effects across restarts or multiple
workers. Do not expose the demonstration as a public API or use real customer
records. The next meaningful milestone is an authenticated boundary and
transactional durable offer consumption, with failure-injection tests.

## Why a separate suite?

The existing 24-case retention policy benchmark measures deterministic
eligibility decisions. This suite measures **session confirmation trust
boundaries**, including side effects and recovery, without changing the
reviewed policy benchmark's fixture or quality gate. It is a regression
baseline, not a claim of increased retention or model quality.
