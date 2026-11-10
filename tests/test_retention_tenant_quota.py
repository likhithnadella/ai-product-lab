"""Tenant-scoped offer quotas: synthetic, deterministic regression cases."""

from decimal import Decimal

import pytest

from app.retention_sessions import SessionRetentionController
from app.retention_simulator import Account, Actor


def tenant(name: str) -> tuple[Account, Actor]:
    account = Account(name, "acct-synthetic", Decimal(60), Decimal(18))
    actor = Actor(name, frozenset({"acct-synthetic"}))
    return account, actor


@pytest.mark.parametrize("limit", [0, -1, 1.5, True, None, "2"])
def test_invalid_tenant_quota_rejected(limit):
    with pytest.raises(ValueError):
        SessionRetentionController(max_pending_offers_per_tenant=limit)


def test_one_tenant_cannot_exhaust_anothers_reserved_quota():
    controller = SessionRetentionController(
        max_pending_offers=3, max_pending_offers_per_tenant=1
    )
    a, actor_a = tenant("tenant-a")
    b, actor_b = tenant("tenant-b")
    first, first_handle = controller.propose(
        a, actor_a, session_id="session-a", amount=Decimal(10)
    )
    denied, denied_handle = controller.propose(
        a, actor_a, session_id="session-a2", amount=Decimal(10)
    )
    second, second_handle = controller.propose(
        b, actor_b, session_id="session-b", amount=Decimal(10)
    )
    assert first.outcome == "offer"
    assert first_handle is not None
    assert denied.reason == "tenant_offer_capacity_reached"
    assert denied_handle is None
    assert second.outcome == "offer"
    assert second_handle is not None
    assert len(controller.pending) == 2


def test_tenant_quota_reclaimed_after_expiry():
    now = [100.0]
    controller = SessionRetentionController(
        max_pending_offers=2,
        max_pending_offers_per_tenant=1,
        ttl_seconds=30,
        clock=lambda: now[0],
    )
    account, actor = tenant("tenant-a")
    _, old = controller.propose(account, actor, session_id="s1", amount=Decimal(10))
    now[0] = 130.0
    response, new = controller.propose(
        account, actor, session_id="s2", amount=Decimal(10)
    )
    assert response.outcome == "offer"
    assert new is not None and new != old
    assert old not in controller.pending


def test_tenant_quota_released_on_decline():
    controller = SessionRetentionController(max_pending_offers_per_tenant=1)
    account, actor = tenant("tenant-a")
    _, old = controller.propose(account, actor, session_id="s1", amount=Decimal(10))
    assert controller.confirm(
        account, actor, session_id="s1", offer_handle=old, decision="decline"
    ).reason == "offer_declined"
    response, new = controller.propose(
        account, actor, session_id="s2", amount=Decimal(10)
    )
    assert response.outcome == "offer"
    assert new is not None
