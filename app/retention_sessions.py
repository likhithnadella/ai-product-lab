"""In-memory, session-bound pending credit offers for a synthetic pilot.

This is NOT authentication or durable transaction storage. The caller must
supply an already-authenticated Actor and a trusted server-side session ID.
A model must never supply identity, session IDs, or confirmation authority.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from secrets import token_urlsafe
from typing import Literal

from app.retention_conversation import Request, Response, resolve
from app.retention_simulator import Account, Actor, CreditSimulator


@dataclass(frozen=True)
class PendingOffer:
    tenant_id: str
    account_id: str
    session_id: str
    amount: Decimal


@dataclass
class SessionRetentionController:
    """One-shot pending offers; no persistence, expiry or concurrency guarantees."""

    simulator: CreditSimulator = field(default_factory=CreditSimulator)
    pending: dict[str, PendingOffer] = field(default_factory=dict)

    def propose(
        self, account: Account, actor: Actor, *, session_id: str, amount: Decimal
    ) -> tuple[Response, str | None]:
        """Issue a random offer handle only after access and policy checks pass."""
        if not session_id or not session_id.strip():
            return Response("escalated", "invalid_session", "verify_identity", ("session_denied",)), None
        result = resolve(account, actor, Request("billing_credit", amount), self.simulator)
        if result.outcome != "offer":
            return result, None
        handle = token_urlsafe(32)
        self.pending[handle] = PendingOffer(
            account.tenant_id, account.account_id, session_id, amount
        )
        return result, handle

    def confirm(
        self,
        account: Account,
        actor: Actor,
        *,
        session_id: str,
        offer_handle: str,
        decision: Literal["accept", "decline"],
    ) -> Response:
        """Consume an offer on acceptance; reject mismatched sessions and identities."""
        if decision not in ("accept", "decline"):
            return Response("escalated", "invalid_decision", "human_review", ("confirmation_denied",))
        if not session_id or not session_id.strip() or not offer_handle:
            return Response("escalated", "invalid_confirmation", "human_review", ("confirmation_denied",))
        offer = self.pending.get(offer_handle)
        if offer is None:
            return Response("escalated", "offer_not_found", "human_review", ("confirmation_denied",))
        if (
            offer.tenant_id != actor.tenant_id
            or offer.tenant_id != account.tenant_id
            or offer.account_id != account.account_id
            or offer.account_id not in actor.authorized_account_ids
            or offer.session_id != session_id
        ):
            return Response("escalated", "unauthorized", "verify_identity", ("confirmation_denied",))
        # A decline invalidates the offer without executing a write.
        if decision == "decline":
            self.pending.pop(offer_handle)
            return Response("escalated", "offer_declined", "human_review", ("offer_declined",))
        # One-shot semantics: a second confirmation must not execute another write.
        self.pending.pop(offer_handle)
        return resolve(
            account,
            actor,
            Request("billing_credit", offer.amount, True, offer_handle),
            self.simulator,
        )
