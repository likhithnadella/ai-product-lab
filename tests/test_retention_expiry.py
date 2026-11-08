"""Expiry, isolation and concurrent confirmation regressions (synthetic only)."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest

from app.retention_sessions import SessionRetentionController
from app.retention_simulator import Account, Actor


@pytest.fixture
def setup():
    now = [100.0]
    account = Account("tenant-a", "acct-synthetic", Decimal(60), Decimal(18))
    actor = Actor("tenant-a", frozenset({"acct-synthetic"}))
    controller = SessionRetentionController(ttl_seconds=30, clock=lambda: now[0])
    return now, account, actor, controller


def test_offer_valid_just_before_expiration(setup):
    now, account, actor, controller = setup
    _, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    now[0] = 129.999
    response = controller.confirm(
        account, actor, session_id="session-a", offer_handle=handle, decision="accept"
    )
    assert response.outcome == "applied"


def test_offer_expires_at_boundary_without_write(setup):
    now, account, actor, controller = setup
    _, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    now[0] = 130.0
    response = controller.confirm(
        account, actor, session_id="session-a", offer_handle=handle, decision="accept"
    )
    assert response.reason == "offer_expired"
    assert handle not in controller.pending
    assert controller.simulator.outcomes == {}


def test_expired_offer_replay_cannot_apply(setup):
    now, account, actor, controller = setup
    _, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    now[0] = 131
    assert controller.confirm(
        account, actor, session_id="session-a", offer_handle=handle, decision="accept"
    ).reason == "offer_expired"
    assert controller.confirm(
        account, actor, session_id="session-a", offer_handle=handle, decision="accept"
    ).reason == "offer_not_found"


def test_unauthorized_confirmation_does_not_consume_offer(setup):
    now, account, actor, controller = setup
    _, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    now[0] = 101
    assert controller.confirm(
        account, actor, session_id="session-other", offer_handle=handle, decision="accept"
    ).reason == "unauthorized"
    assert handle in controller.pending


@pytest.mark.parametrize("ttl", [0, -1, 3601, float("nan"), float("inf")])
def test_invalid_ttl_rejected(ttl):
    with pytest.raises(ValueError):
        SessionRetentionController(ttl_seconds=ttl)


def test_concurrent_acceptance_applies_once(setup):
    _, account, actor, controller = setup
    _, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    barrier = Barrier(2)

    def accept():
        barrier.wait()
        return controller.confirm(
            account, actor, session_id="session-a", offer_handle=handle, decision="accept"
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(accept) for _ in range(2)]
        outcomes = [future.result().outcome for future in futures]
    assert sorted(outcomes) == ["applied", "escalated"]
    assert len(controller.simulator.outcomes) == 1
