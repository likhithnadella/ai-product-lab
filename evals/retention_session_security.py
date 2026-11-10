"""Executable synthetic security evaluations for the retention session boundary.

No real accounts, external services, or model calls. Scenario verdicts compare
observed behavior against explicit expected outcomes, not production metrics.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.retention_sessions import SessionRetentionController
from app.retention_simulator import Account, Actor


@dataclass(frozen=True)
class SessionCase:
    name: str
    mode: str
    expected_reason: str
    expected_applied: int


CASES = (
    SessionCase("accept_valid", "accept", "simulated_credit", 1),
    SessionCase("decline_valid", "decline", "offer_declined", 0),
    SessionCase("cross_tenant", "cross_tenant", "unauthorized", 0),
    SessionCase("wrong_session", "wrong_session", "unauthorized", 0),
    SessionCase("wrong_account", "wrong_account", "unauthorized", 0),
    SessionCase("expired", "expired", "offer_expired", 0),
    SessionCase("replay", "replay", "offer_not_found", 1),
    SessionCase("invalid_decision", "invalid_decision", "invalid_decision", 0),
    SessionCase("capacity", "capacity", "tenant_offer_capacity_reached", 0),
    SessionCase("denial_does_not_consume", "denial_does_not_consume", "simulated_credit", 1),
    SessionCase("expired_releases_quota", "expired_releases_quota", "confirmation_required", 0),
)


def run_case(case: SessionCase) -> dict[str, object]:
    """Execute one isolated scenario with a controlled monotonic clock."""
    now = [100.0]
    controller = SessionRetentionController(
        ttl_seconds=30.0,
        max_pending_offers_per_tenant=1,
        clock=lambda: now[0],
    )
    account = Account("tenant-a", "account-a", Decimal(60), Decimal(18))
    actor = Actor("tenant-a", frozenset({"account-a"}))
    proposal, handle = controller.propose(
        account, actor, session_id="session-a", amount=Decimal(10)
    )
    assert proposal.outcome == "offer" and handle is not None
    if case.mode == "expired_releases_quota":
        now[0] = 130.0
        result, replacement = controller.propose(
            account, actor, session_id="session-b", amount=Decimal(10)
        )
        observed_reason = result.reason
        assert replacement is not None and replacement != handle
    elif case.mode == "capacity":
        result, _ = controller.propose(
            account, actor, session_id="session-b", amount=Decimal(10)
        )
        observed_reason = result.reason
    else:
        target_account = account
        target_actor = actor
        target_session = "session-a"
        decision = "accept"
        if case.mode == "decline":
            decision = "decline"
        elif case.mode == "cross_tenant":
            target_actor = Actor("tenant-b", frozenset({"account-a"}))
        elif case.mode == "wrong_session":
            target_session = "session-b"
        elif case.mode == "wrong_account":
            target_account = Account(
                "tenant-a", "account-b", Decimal(60), Decimal(18)
            )
            target_actor = Actor("tenant-a", frozenset({"account-a", "account-b"}))
        elif case.mode == "expired":
            now[0] = 130.0
        elif case.mode == "invalid_decision":
            decision = "approve"
        elif case.mode == "denial_does_not_consume":
            target_actor = Actor("tenant-b", frozenset({"account-a"}))
        result = controller.confirm(
            target_account, target_actor, session_id=target_session,
            offer_handle=handle, decision=decision,
        )
        if case.mode == "denial_does_not_consume":
            assert result.reason == "unauthorized"
            result = controller.confirm(
                account, actor, session_id="session-a",
                offer_handle=handle, decision="accept",
            )
        if case.mode == "replay":
            result = controller.confirm(
                account, actor, session_id="session-a",
                offer_handle=handle, decision="accept",
            )
        observed_reason = result.reason
    applied = sum(
        action.status == "applied"
        for _, action in controller.simulator.outcomes.values()
    )
    return {
        "name": case.name,
        "expected_reason": case.expected_reason,
        "observed_reason": observed_reason,
        "expected_applied": case.expected_applied,
        "observed_applied": applied,
        "passed": (
            observed_reason == case.expected_reason
            and applied == case.expected_applied
        ),
    }


def run_suite() -> dict[str, object]:
    results = [run_case(case) for case in CASES]
    return {
        "suite": "retention-session-security-v1",
        "cases": len(results),
        "passed": sum(bool(row["passed"]) for row in results),
        "failed": sum(not row["passed"] for row in results),
        "results": results,
    }


if __name__ == "__main__":
    import json

    report = run_suite()
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["failed"]:
        raise SystemExit(1)
