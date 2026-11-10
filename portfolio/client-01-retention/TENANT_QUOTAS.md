# Retention offer quotas — design note (2026-11-09)

**Scope:** Fictional subscription provider, synthetic accounts only. This is not a production deployment.

## Threat and objective

The prior process-wide pending-offer limit prevents unbounded growth but permits a single tenant to consume the entire shared pool. This change adds a configurable **per-tenant limit** while retaining the global ceiling. Tenant identity is obtained from the trusted account after the existing authorization and policy checks; it is **not** a user-supplied free-form quota key.

## Behavior and invariants

- Both limits are positive integers; booleans, floats and invalid values fail during initialization.
- Proposals run under the existing controller lock. Expired handles are reclaimed before either capacity check.
- The global ceiling takes precedence when both limits are exhausted. A tenant-specific denial uses `tenant_offer_capacity_reached` and returns no handle.
- Denied proposals do not create pending offers or apply credits.
- Decline, successful confirmation and expiration free capacity. Unauthorized confirmation cannot consume or release another tenant's offer.
- Existing policy checks still run **before** capacity accounting.

## Tradeoffs

This uses an O(N) count of pending offers on each eligible proposal, where N is bounded by `max_pending_offers` (default 1000). This is simpler and safer than maintaining a second mutable counter, which could drift on expiry or exception paths. For a durable distributed implementation, replace this with transactional per-tenant and global counters, expiry leases, rate limiting, authenticated tenant context and metrics.

**Important limitation:** quotas are process-local, not distributed, and do not constitute API rate limiting, authentication or denial-of-service protection. The default per-tenant cap (100) is a prototype configuration choice, not a measured production sizing recommendation.

## Verification

Run:

```sh
ruff check app/retention_sessions.py tests/test_retention_tenant_quota.py tests/test_retention_tenant_quota_security.py
pytest -q tests/test_retention_capacity.py tests/test_retention_expiry.py tests/test_retention_tenant_quota.py tests/test_retention_tenant_quota_security.py
```

Expected coverage: quota validation, tenant isolation, global capacity precedence, expiration, decline, unauthorized proposal/confirmation. Actual pass/fail must be taken from CI, not inferred from this document.
