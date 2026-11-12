# Tenant-scoped retrieval: pagination and trust boundary

This prototype is **not a deployable authenticated API**. It is an internal, process-local
storage experiment. The existing unauthenticated demo endpoints remain disabled by default
and are **not** connected to `TenantRecordStore`.

## Threat and boundary

- A caller may control query text, requested page size and offset; those inputs must
  never determine tenant ownership or source grants.
- A trusted identity adapter must derive `TenantPrincipal` from a verified session or
  service identity and authoritative entitlements. Never deserialize this object directly
  from HTTP JSON or treat source filters supplied by the caller as authorization.
- Storage keys include tenant identity. Read and write permissions are checked by source;
  retrieval filters records by both tenant and readable source **before ranking and paging**.
- Pagination reuses the lexical search limit (1–100) and offset (0–10,000) validation.
  Offset paging is not a stable snapshot under concurrent writes. Production should use
  a cursor tied to a consistent snapshot, with signed/opaque cursor state and authorization
  rechecked on every request.

## Reproduce

```bash
ruff check app/tenant_store.py tests/test_tenant_search_pagination.py
pytest -q tests/test_tenant_store.py tests/test_tenant_search_pagination.py
```

The new synthetic tests check that pages exclude other tenants and unauthorized sources,
that out-of-range offsets fail, and that principals with no read grants see no results.

## Deliberate exclusions

No JWT verification, session binding, entitlement refresh, per-record ACL, tenant-specific
rate limits, database row-level security, audit log or distributed storage is implemented.
A process-local Python principal can be constructed by arbitrary application code and
therefore is **not** a proof of caller identity. Do not deploy these internals as an
internet-facing multi-tenant service.

## Next milestone

Design a verified identity adapter and a durable database with tenant ownership enforced
at the query/transaction boundary. Add integration tests that attempt cross-tenant
ingestion, point reads and retrieval through the real authenticated API before enabling it.
