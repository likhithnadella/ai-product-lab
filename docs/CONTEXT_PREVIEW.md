# Local tenant-scoped context preview (synthetic prototype)

## Why this slice exists

Before adding a model or a public search endpoint, we need a reproducible
**retrieval-to-evidence** contract: authorized records, stable provenance,
explicit abstention, and a narrow field projection. This demonstrates the
boundary that future grounded model calls would consume, without claiming
that a prompt or model can enforce access control.

Run from the repository root after installing development dependencies:

```bash
python -m app.context_demo
pytest -q tests/test_context_preview.py tests/test_context_demo.py
ruff check app/context_preview.py app/context_demo.py tests/test_context_preview.py tests/test_context_demo.py
```

The demo uses invented names and identifiers, writes only to a process-local
store, and prints a deterministic JSON report. It shows one CRM record visible
to tenant A, while a partner-source record and a tenant B record are excluded.
A missing query returns `abstained: true`, with no invented answer.

## Contract

`assemble_context(store, principal, query, max_hits=5)` returns a
`ContextPreview` containing a tuple of `ContextEvidence` entries.
Each entry carries the source and external ID, lexical score, matched-field
names, and only nonblank first name, last name, and company fields.
Email, phone, and arbitrary attributes are **not projected**. The caller
can ask for 1–20 hits; booleans, nonintegers, and out-of-range limits fail.
Blank and non-string queries fail. Empty evidence explicitly abstains.

This is **structured untrusted data**, not a safe prompt, a citation-verified
generated answer, or an LLM evaluation. Identifiers, names, and companies may
still be sensitive in real deployments. Never log or publish real previews.

## Trust boundary and limitations

- `TenantPrincipal` is currently constructible by any Python caller. The
  prototype assumes a trusted in-process caller; it does **not** authenticate
  identity. A production caller must derive it from verified credentials and
  centrally enforced authorization, not a request body or model output.
- `TenantRecordStore.search` applies tenant and readable-source filtering
  before retrieval. Source scopes alone are not record-level authorization.
- No HTTP endpoint exposes this preview. The existing opt-in unauthenticated
  demo endpoints remain local-only and are not made safer by this feature.
- The store is in memory, without durability, multi-worker consistency, rate
  limiting, audit history, or cross-process authorization.
- A future model must treat every retrieved field as untrusted text. Prompt
  injection, output disclosure, tool permissions, and citation verification
  remain unsolved. Do not insert these fields into a system prompt.
- A lexical match score is not a calibrated confidence probability.
  Abstention means no lexical evidence was returned, not proof of absence.

## Testable evidence and next decisions

The tests cover ranked provenance, narrow projection, tenant isolation,
source-level denial, empty results, invalid queries/limits, and a synthetic
end-to-end demonstration. CI results should be verified on the PR before
merging. These tests are not penetration testing or production measurements.

Next: add a server-derived identity boundary and record-level permissions
(issue #8), then a provider-independent model adapter and grounded-answer
evaluation with explicit provenance and refusal cases. Only after those gates
should a model-facing or public retrieval endpoint be considered.
