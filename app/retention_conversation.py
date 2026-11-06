"""Bounded, deterministic conversation controller for a synthetic retention pilot.

This is NOT an LLM agent. A future language model may propose intent, but only
trusted identity, policy and explicit user confirmation can authorize actions.
No raw dialogue or customer identifiers are written to the trace.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from app.retention_simulator import Account, Actor, CreditSimulator, assess_credit

Intent = Literal["billing_credit", "cancel", "unknown"]
Outcome = Literal["offer", "applied", "escalated"]


@dataclass(frozen=True)
class Request:
    intent: Intent
    requested_credit: Decimal = Decimal("0.00")
    confirmed: bool = False
    idempotency_key: str = ""


@dataclass(frozen=True)
class Response:
    outcome: Outcome
    reason: str
    next_step: str
    trace: tuple[str, ...]


def resolve(
    account: Account,
    actor: Actor,
    request: Request,
    simulator: CreditSimulator,
) -> Response:
    """Run a single controlled turn; no account mutation before confirmation."""
    trace = ("intent_received",)
    # Check identity before discussing account-specific eligibility.
    if account.tenant_id != actor.tenant_id or account.account_id not in actor.authorized_account_ids:
        return Response("escalated", "unauthorized", "verify_identity", trace + ("access_denied",))
    if request.intent == "unknown":
        return Response("escalated", "ambiguous_intent", "human_review", trace + ("abstained",))
    if request.intent == "cancel":
        # There is no cancellation write integration in the simulator.
        return Response("escalated", "cancellation_not_implemented", "human_review", trace + ("no_action",))
    if request.intent != "billing_credit":
        # Fail closed even if an untyped caller passes an unexpected string.
        return Response("escalated", "unsupported_intent", "human_review", trace + ("no_action",))
    decision = assess_credit(account, actor)
    if not decision.eligible:
        return Response("escalated", decision.reason, "human_review", trace + ("policy_denied",))
    amount = request.requested_credit
    if not amount.is_finite() or amount <= 0 or amount > decision.maximum_credit:
        return Response("escalated", "outside_policy", "human_review", trace + ("policy_denied",))
    if not request.confirmed:
        return Response("offer", "confirmation_required", "ask_explicit_confirmation",
                        trace + ("policy_eligible", "awaiting_confirmation"))
    result = simulator.apply(
        account,
        actor,
        amount,
        confirmed=True,
        idempotency_key=request.idempotency_key,
    )
    if result.status != "applied":
        return Response("escalated", result.reason, "human_review", trace + ("action_rejected",))
    return Response("applied", result.reason, "complete", trace + ("action_applied",))
