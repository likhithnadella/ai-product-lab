"""In-memory, session-bound expiring credit offers for a synthetic pilot.

NOT authentication, durable transactions, or distributed concurrency control.
Callers must supply a trusted authenticated Actor and server-side session ID.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal
from math import isfinite
from secrets import token_urlsafe
from threading import RLock
from time import monotonic
from typing import Literal

from app.retention_conversation import Request, Response, resolve
from app.retention_simulator import Account, Actor, CreditSimulator


@dataclass(frozen=True)
class PendingOffer:
    tenant_id: str
    account_id: str
    session_id: str
    amount: Decimal
    expires_at: float


@dataclass
class SessionRetentionController:
    """Process-local, expiring one-shot offers with serialized confirmation."""

    simulator: CreditSimulator = field(default_factory=CreditSimulator)
    pending: dict[str, PendingOffer] = field(default_factory=dict)
    ttl_seconds: float = 300.0
    max_pending_offers: int = 1000
    max_pending_offers_per_tenant: int = 100
    clock: Callable[[], float] = monotonic
    _lock: RLock = field(default_factory=RLock, repr=False)

    def __post_init__(self) -> None:
        if not isfinite(self.ttl_seconds) or not 0 < self.ttl_seconds <= 3600:
            raise ValueError("ttl_seconds must be within (0, 3600]")
        if type(self.max_pending_offers) is not int or self.max_pending_offers < 1:
            raise ValueError("max_pending_offers must be a positive integer")
        if type(self.max_pending_offers_per_tenant) is not int or self.max_pending_offers_per_tenant < 1:
            raise ValueError("max_pending_offers_per_tenant must be a positive integer")

    def _prune_expired(self, now: float) -> None:
        """Reclaim expired handles while holding the controller lock."""
        expired = [key for key, offer in self.pending.items() if now >= offer.expires_at]
        for key in expired:
            self.pending.pop(key, None)

    def propose(
        self, account: Account, actor: Actor, *, session_id: str, amount: Decimal
    ) -> tuple[Response, str | None]:
        """Issue an expiring random offer handle after authorization and policy checks."""
        if not session_id or not session_id.strip():
            return Response("escalated", "invalid_session", "verify_identity", ("session_denied",)), None
        with self._lock:
            result = resolve(account, actor, Request("billing_credit", amount), self.simulator)
            if result.outcome != "offer":
                return result, None
            now = self.clock()
            self._prune_expired(now)
            if len(self.pending) >= self.max_pending_offers:
                return (
                    Response("escalated", "offer_capacity_reached", "human_review", ("capacity_denied",)),
                    None,
                )
            tenant_pending = sum(
                offer.tenant_id == account.tenant_id for offer in self.pending.values()
            )
            if tenant_pending >= self.max_pending_offers_per_tenant:
                return (
                    Response("escalated", "tenant_offer_capacity_reached", "human_review", ("capacity_denied",)),
                    None,
                )
            handle = token_urlsafe(32)
            self.pending[handle] = PendingOffer(
                account.tenant_id, account.account_id, session_id, amount,
                now + self.ttl_seconds,
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
        """Authorize, check expiry, then consume and resolve under a process-local lock."""
        if decision not in ("accept", "decline"):
            return Response("escalated", "invalid_decision", "human_review", ("confirmation_denied",))
        if not session_id or not session_id.strip() or not offer_handle:
            return Response("escalated", "invalid_confirmation", "human_review", ("confirmation_denied",))
        with self._lock:
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
            if self.clock() >= offer.expires_at:
                self.pending.pop(offer_handle)
                return Response("escalated", "offer_expired", "human_review", ("confirmation_denied",))
            self.pending.pop(offer_handle)
            if decision == "decline":
                return Response("escalated", "offer_declined", "human_review", ("offer_declined",))
            return resolve(
                account, actor, Request("billing_credit", offer.amount, True, offer_handle),
                self.simulator,
            )
