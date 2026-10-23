# Tenant isolation and authentication: pre-deployment contract

Status: **design only**. This repository has no authenticated ingestion or authorized retrieval API. **Do not deploy publicly or ingest customer data.** This document defines the security contract for [issue #8](https://github.com/likhithnadella/ai-product-lab/issues/8), not a claim that it is implemented.

## Current trust boundaries

- `POST /v1/ingest` accepts records without a caller identity. A process-global `InMemoryRecordStore` keys records by `(source, external_id)` only.
- `POST /v1/resolve` accepts arbitrary candidate records without checking caller rights.
- Internal lexical search accepts `allowed_sources` from its caller. That filter is **not** proof of authorization and must not be exposed as a user-controlled access policy.
- Process-local storage is neither durable nor isolated between tenants; restarts lose data.

## Required design before any public deployment

1. **Trusted identity:** authenticate requests at the service boundary. Validate signature, issuer, audience, expiry and key rotation of externally issued credentials. Reject missing or invalid credentials before touching records. Never trust caller-supplied tenant identifiers alone.
2. **Tenant ownership:** associate each persisted record with a server-derived `tenant_id`. Uniqueness becomes `(tenant_id, source, external_id)`; tenant identity is immutable through ordinary update paths.
3. **Authorization:** derive the allowed tenant and permitted operations from validated claims and a server-side policy. Ingest requires write permission for that tenant/source; read and retrieval require explicit read permission. Never let `allowed_sources` expand the authenticated scope.
4. **Defense in depth:** require tenant predicates in every storage query and retrieval candidate filter, including batch and replay paths. Deny on missing scope, inconsistent tenant claims, or policy failures.
5. **Auditing and minimization:** log actor, tenant, operation, decision, request correlation ID and outcome, not raw records, email addresses, tokens or secret-bearing headers. Apply rate limits and payload-size limits.
6. **Deployment:** require TLS, a secret manager, restrictive network exposure and a durable storage design before external traffic. Local development may use synthetic fixtures only.

## Negative test plan (not yet implemented)

| Scenario | Required outcome |
|---|---|
| Unauthenticated ingest or read | 401; no record access or mutation |
| Valid identity without tenant permission | 403; no data disclosure |
| Tenant A writes same source/external ID as B | Independent records; no overwrite |
| Tenant A searches for B's unique identifier | No B records or metadata in results |
| Caller supplies B in source filters or request body | Server-derived tenant scope still enforced |
| Batch mixes authorized and unauthorized tenant records | Reject unauthorized records without side effects; explicitly define atomicity |
| Tenant changes on replay/update | Reject or create a separately authorized migration operation |
| Invalid/expired token or policy backend failure | Fail closed |

## Implementation sequence

Start with a trusted principal contract and negative API tests, then tenant-aware record keys and storage methods, then scoped retrieval, then audit/operational controls. Each increment needs passing CI and independent review. **Do not treat this design document as a completed security control.**
