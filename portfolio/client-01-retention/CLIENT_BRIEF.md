# Client 01 — Subscription Retention & Customer Resolution

> **Simulation only.** This is an original fictional client engagement with synthetic data, not a Sierra customer project or real production deployment.

## Business problem
A fictional subscription provider has customers requesting cancellation after billing disputes. Human agents must interpret account context, billing history, retention policies and customer intent before offering a resolution. We want to determine whether a bounded AI agent can resolve eligible requests safely and efficiently.

## Desired outcome
Increase correct end-to-end resolution of eligible customer requests while preserving customer choice, avoiding unauthorized concessions and escalating ambiguous or sensitive situations.

## Personas and stakeholders
- Subscriber: wants an understandable, fair resolution and control over cancellation.
- Customer operations lead: wants consistent resolution and measurable quality.
- Billing/policy owner: controls permissible adjustments.
- Security/compliance owner: requires authorized actions and audit records.
- Support specialist: receives escalated cases with useful context.

## Proposed pilot workflow
1. Subscriber asks to cancel due to an unexpected charge.
2. Agent retrieves a **synthetic** account and billing history through scoped tools.
3. Agent obtains versioned policy evidence and determines eligibility.
4. Agent explains available options without inventing discounts.
5. Agent asks for explicit confirmation before any account-changing action.
6. Authorized simulator applies an adjustment or cancellation idempotently; otherwise the case escalates.
7. Trace records evidence, tool inputs/outcomes and resolution status.

## Design alternatives
| Option | Strength | Limitation |
| --- | --- | --- |
| Deterministic workflow only | Predictable and easy to audit | Brittle for varied language and context |
| Unconstrained LLM agent | Flexible dialogue | Unacceptable action and policy risks |
| **Recommended: bounded agent + deterministic policy/action engine** | Flexible dialogue with enforceable controls | More integration and test effort |

## Non-negotiable controls
- Never trust the model to grant permissions or determine policy limits by itself.
- Enforce tenant and account authorization outside the model.
- Reject unauthorized offers and actions at the tool boundary.
- Require explicit user confirmation for changes.
- Use idempotency keys for writes and preserve replay safety.
- Treat retrieved documents and user messages as untrusted instructions.
- No real subscriber data, payment credentials or production systems.

## Evaluation plan
Use >=20 synthetic scenarios: eligible billing dispute, ineligible concession, cancellation-only, missing account, conflicting policy, prompt injection, stale data, ambiguous intent, duplicate request, tool timeout, retry and escalation.

Compare a deterministic baseline with the bounded agent on:
- End-to-end task success and correct action rate
- Unauthorized action attempts accepted (target: zero)
- Appropriate escalation rate
- p95 latency and estimated model cost per successful resolution
- Recovery from tool failure and replay

**Report actual measured results only.** Do not claim improved retention or human-agent outperformance without an appropriate real-world study.

## Definition of done
- Runnable local end-to-end flow with synthetic fixtures
- Tests, lint and security checks in CI
- Evaluation scenarios and reproducible report
- Architecture decisions, failure analysis, deployment instructions and short demo
- Independent review before merging

## Next implementation PR
Implement typed synthetic account, billing and policy data; deterministic eligibility service; safe action simulator with confirmation/idempotency; unit and integration tests. Add LLM orchestration only after the deterministic controls pass.
