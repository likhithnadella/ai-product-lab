"""Synthetic, local-only subscription resolution policy and action simulator.

The policy engine is deterministic. No model text can grant authorization.
This module is not a payment, billing, or identity verification integration.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class Account:
    tenant_id: str
    account_id: str
    monthly_charge: Decimal
    disputed_charge: Decimal
    active: bool = True


@dataclass(frozen=True)
class Actor:
    tenant_id: str
    authorized_account_ids: frozenset[str]


@dataclass(frozen=True)
class Decision:
    eligible: bool
    reason: str
    maximum_credit: Decimal = Decimal("0.00")


def assess_credit(account: Account, actor: Actor) -> Decision:
    """Return a policy decision, never trusting user/LLM-supplied eligibility."""
    if account.tenant_id != actor.tenant_id:
        return Decision(False, "unauthorized")
    if account.account_id not in actor.authorized_account_ids:
        return Decision(False, "unauthorized")
    if not account.active:
        return Decision(False, "inactive")
    if not account.monthly_charge.is_finite() or not account.disputed_charge.is_finite():
        return Decision(False, "invalid_amount")
    if account.monthly_charge <= 0 or account.disputed_charge <= 0:
        return Decision(False, "invalid_amount")
    if account.disputed_charge > account.monthly_charge:
        return Decision(False, "requires_review")
    return Decision(True, "eligible", min(account.disputed_charge, Decimal("25.00")))


@dataclass(frozen=True)
class ActionResult:
    status: Literal["applied", "rejected"]
    reason: str
    credit: Decimal = Decimal("0.00")


@dataclass
class CreditSimulator:
    """In-memory demonstration only: idempotency is NOT durable across restarts."""

    outcomes: dict[tuple[str, str], tuple[tuple[str, str, Decimal], ActionResult]] = field(
        default_factory=dict
    )

    def apply(
        self,
        account: Account,
        actor: Actor,
        amount: Decimal,
        *,
        confirmed: bool,
        idempotency_key: str,
    ) -> ActionResult:
        if not idempotency_key or not idempotency_key.strip() or len(idempotency_key) > 128:
            return ActionResult("rejected", "invalid_idempotency_key")
        key = (actor.tenant_id, idempotency_key)
        fingerprint = (account.tenant_id, account.account_id, amount)
        # Recheck authorization even for a replay; keys do not grant account access.
        if not assess_credit(account, actor).eligible:
            return ActionResult("rejected", "unauthorized_or_ineligible")
        if not confirmed:
            return ActionResult("rejected", "confirmation_required")
        if key in self.outcomes:
            prior_fingerprint, prior_result = self.outcomes[key]
            if prior_fingerprint != fingerprint:
                return ActionResult("rejected", "idempotency_conflict")
            return prior_result
        decision = assess_credit(account, actor)
        if not decision.eligible:
            return ActionResult("rejected", decision.reason)
        if not amount.is_finite() or amount <= 0 or amount > decision.maximum_credit:
            return ActionResult("rejected", "outside_policy")
        result = ActionResult("applied", "simulated_credit", amount)
        self.outcomes[key] = (fingerprint, result)
        return result
