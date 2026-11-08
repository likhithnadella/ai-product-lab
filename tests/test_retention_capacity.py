"""Capacity, expiry reclamation and safe denial regressions (synthetic only)."""

from decimal import Decimal

import pytest

from app.retention_sessions import SessionRetentionController
from app.retention_simulator import Account, Actor


def setup_controller(capacity=1):
    now = [100.0]
    account = Account("tenant-a", "acct-synthetic", Decimal(60), Decimal(18))
    actor = Actor("tenant-a", frozenset({"acct-synthetic"}))
    controller = SessionRetentionController(
        max_pending_offers=capacity, ttl_seconds=30, clock=lambda: now[0]
    )
    return now, account, actor, controller


@pytest.mark.parametrize("capacity", [0, -1, 1.5, True, None, "10"])
def test_invalid_capacity_rejected(capacity):
    with pytest.raises(ValueError):
        SessionRetentionController(max_pending_offers=capacity)


def test_capacity_denial_preserves_existing_offer():
    _, account, actor, controller = setup_controller()
    _, handle = controller.propose(account, actor, session_id="s1", amount=Decimal(10))
    response, denied = controller.propose(
        account, actor, session_id="s2", amount=Decimal(10)
    )
    assert response.reason == "offer_capacity_reached"
    assert denied is None
    assert list(controller.pending) == [handle]
    assert controller.simulator.outcomes == {}


def test_expired_handle_reclaimed_on_next_proposal():
    now, account, actor, controller = setup_controller()
    _, first = controller.propose(account, actor, session_id="s1", amount=Decimal(10))
    now[0] = 130.0
    response, second = controller.propose(
        account, actor, session_id="s2", amount=Decimal(10)
    )
    assert response.outcome == "offer"
    assert second is not None and second != first
    assert first not in controller.pending
    assert len(controller.pending) == 1
    assert controller.confirm(
        account, actor, session_id="s1", offer_handle=first, decision="accept"
    ).reason == "offer_not_found"


def test_consumed_offer_frees_capacity():
    _, account, actor, controller = setup_controller()
    _, first = controller.propose(account, actor, session_id="s1", amount=Decimal(10))
    assert controller.confirm(
        account, actor, session_id="s1", offer_handle=first, decision="decline"
    ).reason == "offer_declined"
    response, second = controller.propose(
        account, actor, session_id="s2", amount=Decimal(10)
    )
    assert response.outcome == "offer"
    assert second is not None


def test_policy_denial_does_not_use_capacity():
    _, account, actor, controller = setup_controller()
    unauthorized = Actor("tenant-other", frozenset({"acct-synthetic"}))
    response, handle = controller.propose(
        account, unauthorized, session_id="s1", amount=Decimal(10)
    )
    assert response.outcome != "offer"
    assert handle is None
    assert controller.pending == {}
