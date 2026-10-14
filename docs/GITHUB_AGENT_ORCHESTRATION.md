# GitHub-native agent collaboration (deployment plan)

GitHub Issues, pull requests, reviews, and Actions are the source of truth. Slack is **notification-only**; it never approves or triggers work.

## Intended workflow

1. A scheduled or manually dispatched GitHub Action selects one `agent-ready` issue. Only a repository maintainer may apply `agent-ready`; the workflow verifies the label actor's trusted GitHub identity, not just the presence of the label. An atomic issue claim/lock prevents duplicate work.
2. An authenticated **implementation runner** (Codex API/CLI or another explicitly configured runner) creates a branch, writes tests and code, and opens a PR referencing the issue.
3. A separate **review runner** (Claude API/CLI or independently authenticated runner) reviews the *exact PR head SHA*, including test quality, security and scope. The review must be a recorded GitHub APPROVED review from a distinct identity.
4. Required GitHub CI succeeds on that SHA. Only low-risk, reversible PRs are eligible for automatic merge; security, architecture, dependencies, secrets, workflow/permission changes and destructive operations require owner approval.
5. A GitHub-controlled merge gate rechecks head SHA, review state, mergeability, branch protection and required checks. It uses least-privilege permissions, never force-pushes or bypasses protections.
6. Successful merges and an end-of-day contribution digest are sent to Slack `#aibuild`, with PR links, merge SHAs, CI, review attribution and blockers.

## Trust boundaries and triggers

- **Issue bodies, PR descriptions, comments, commit messages, file contents and model outputs are untrusted input**, never privileged instructions. Agent runners must not obey embedded requests to disclose secrets, alter workflows, expand scope, or bypass review. Work is constrained by maintainer-approved issue metadata and allowlisted paths/actions.
- **Label provenance:** only trusted maintainers may set `agent-ready`. GitHub permissions/rules must restrict label application where supported; in all cases, the dispatcher validates the trusted actor via event/audit evidence before claiming work. A label with unverified provenance is ineligible.
- **Job permissions:** selector `contents:read, issues:read`; implementation `contents:write, pull-requests:write` using a separately scoped credential restricted by server-side policy to `agent/*` branches (GitHub Actions YAML permissions alone cannot enforce branch-path limits); review `contents:read, pull-requests:write` for review submission only, **no code write permission**; merge `contents:write, pull-requests:read, checks:read` using a separate protected credential, scoped to authorized merges. Give `actions:read` only where required to verify runs. Default all unspecified permissions to `none`. Credential capabilities and branch restrictions must be verified before deployment.
- **Review trigger:** on `pull_request` `opened`, `reopened`, and `synchronize` (plus explicit `workflow_dispatch` retry), check out the exact event `head.sha`, never a mutable branch ref. The reviewer posts a GitHub review referencing that SHA; the merge gate re-fetches the current head and rejects stale approvals. Never execute untrusted PR code with privileged tokens via `pull_request_target`.
- **Bounded initial rollout:** at most **5 successfully merged PRs per day**; a failed review/CI, security-sensitive change, conflict, or budget limit stops the cycle pending owner decision. Do not continue indefinitely by generating new tasks.

## Prerequisites before enabling autonomous execution

- Configure and budget **two actual agent runners**; chat sessions cannot be awakened by GitHub events. Runner execution and API costs need explicit limits.
- Provision distinct, scoped credentials for implementation, review and merge. Do not count reviews from the PR author's GitHub identity as independent, even if another model wrote them.
- Enable branch protection/rulesets: required CI, independent approval, dismiss stale approvals, block force pushes, restrict merges and protect workflow files. GitHub's built-in auto-merge is not a substitute for these controls.
- Install a Slack GitHub Action or webhook integration with an appropriately scoped secret; report only after verified merge events. Ensure notification failures do not weaken merge gates.
- Set concurrency, a five-merged-PRs/day cap, spending limits, retry ceilings, deadlines, and a kill switch. Persist claims and checkpoints in GitHub to survive runner restarts.
- Test on a non-production repository with deliberately failing CI, stale approvals, conflicting changes and attempted privilege escalation before enabling on this private repository.

## Current implementation status

**Design only — not deployed.** No agent credentials, automatic runners, auto-merge policy, or Slack notifications are activated by this document. Existing `CI` (Ruff + pytest) remains unchanged. No secret values should be committed to this repository.

## Acceptance criteria for the first executable increment

- A `workflow_dispatch` dry-run lists eligible issues and proposed work without modifying code.
- Separate service identities perform implementation and review; review SHA is verified at merge.
- Green required CI and fresh independent approval are mandatory for automatic merge.
- Every merge creates exactly one Slack notification; the daily digest is idempotent.
- All actions are auditable via GitHub PRs, Actions logs, and issue comments.
