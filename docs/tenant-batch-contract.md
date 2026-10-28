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

1. Consume at most **1,001** iterable items, rejecting any batch larger
   than **1,000 records** before modifying storage. The 1,001st item is
   inspected only to detect overflow; it is never copied or persisted.
   Validate each accepted item and its source permission. Invalid items,
   overflow, iterator exceptions, or defensive-copy failures leave the
   entire batch unapplied.
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
- The iterable is copied in memory up to a hard limit of **1,000 records**.
  Overflow raises `ValueError` and preserves existing state; generators are
  stopped after the 1,001st yield. This bounds record count, **not bytes**:
  large attribute payloads, concurrent calls, and the full copied batch can
  still consume substantial memory. Callers must enforce input-byte budgets,
  concurrency controls, and timeouts separately. This method is **not** an
  HTTP body limit, total-memory quota, or defense against slow iterators.
- It does not enforce per-record ACLs, event ordering/version monotonicity,
  authentication, or tenant derivation from verified tokens.
- The current public-facing demo routes are separate and must remain
  fail-closed until a trusted authentication and authorization boundary exists.

## Regression evidence

`pytest tests/test_tenant_store.py` covers cross-tenant isolation, denied
source access, preflight rejection without partial writes, duplicate-key
ordering, iterator failure, 1,000-item acceptance and overflow rejection, bounded
iterator consumption, and input/output copy boundaries. Full CI must
also pass; an independent review is required before merging.
