# Tenant-scoped batch write contract (internal prototype)

The `TenantRecordStore.upsert_many(principal, records)` API is an **internal,
process-local** operation, introduced as an incremental part of issue #8. It
does not expose a new HTTP route or authenticate a caller.

## Trusted boundary

A trusted server-side identity/authorization layer must construct
`TenantPrincipal` from verified credentials and grant readable/writable
sources. Never construct it from request-supplied tenant IDs or source scopes.
`TenantPrincipal` is an ordinary Python object, **not a cryptographic or
unforgeable capability**; the internal API alone is not an authorization
solution for arbitrary Python callers.

The store keys records by `(tenant_id, source, external_id)`. Every batch
item must have a nonblank source and external ID, and its source must be
writable by the principal. Missing permission raises `PermissionError`.

## Processing semantics

1. Consume the iterable and validate **every** item and its source permission
   before modifying storage. Invalid items, an iterator exception, or a
   defensive-copy failure leave the batch unapplied.
2. Deep-copy inputs before taking the process-local lock.
3. Under one lock, classify each item in input order as `created`,
   `updated`, or `unchanged`. Repeated keys within the batch observe
   earlier writes in that batch.
4. Return statuses in input order. Empty batches return `[]` but still
   require a trusted principal.

Example using entirely synthetic identities:

```python
from app.models import IntakeRecord
from app.tenant_store import TenantPrincipal, TenantRecordStore

store = TenantRecordStore()
actor = TenantPrincipal(
    tenant_id="demo-tenant",
    writable_sources=frozenset({"synthetic-crm"}),
)
result = store.upsert_many(
    actor,
    [IntakeRecord(source="synthetic-crm", external_id="demo-1")],
)
assert result == ["created"]
```

## Limits and follow-up work

- Atomicity and locking apply **only inside one Python process**. There is
  no durable transaction, cross-worker coordination, rollback after process
  failure, or persistent audit trail. Use a database unique constraint and
  transaction when implementing durable storage.
- The iterable is materialized and copied in memory. The caller must enforce
  an appropriate batch-size budget; this method is **not** an HTTP body limit
  or resource quota.
- It does not enforce per-record ACLs, event ordering/version monotonicity,
  authentication, or tenant derivation from verified tokens.
- The current public-facing demo routes are separate and must remain
  fail-closed until a trusted authentication and authorization boundary exists.

## Regression evidence

`pytest tests/test_tenant_store.py` covers cross-tenant isolation, denied
source access, preflight rejection without partial writes, duplicate-key
ordering, iterator failure, and input/output copy boundaries. Full CI must
also pass; an independent review is required before merging.
