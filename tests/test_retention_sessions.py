"""Security contracts for session-bound synthetic credit confirmation."""

from decimal import Decimal

import pytest

from app.retention_sessions import SessionRetentionController
from app.retention_simulator import Account, Actor


@pytest.fixture
def context():
    account = Account("tenant-a", "acct-synthetic", Decimal(60), Decimal(18))
    actor = Actor("tenant-a", frozenset({"acct-synthetic"}))
    return account, actor, SessionRetentionController()


def test_proposal_requires_confirmation_and_does_not_write(context):
    account, actor, controller = context
    result, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    assert result.outcome == "offer"
    assert handle and len(handle) >= 32
    assert controller.simulator.outcomes == {}


def test_same_session_confirmation_applies_once(context):
    account, actor, controller = context
    _, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    first = controller.confirm(
        account, actor, session_id="session-a", offer_handle=handle, decision="accept"
    )
    second = controller.confirm(
        account, actor, session_id="session-a", offer_handle=handle, decision="accept"
    )
    assert first.outcome == "applied"
    assert second.reason == "offer_not_found"
    assert len(controller.simulator.outcomes) == 1


def test_other_session_cannot_accept_offer(context):
    account, actor, controller = context
    _, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    result = controller.confirm(
        account, actor, session_id="session-b", offer_handle=handle, decision="accept"
    )
    assert result.reason == "unauthorized"
    assert controller.simulator.outcomes == {}
    assert handle in controller.pending


def test_cross_tenant_actor_cannot_confirm(context):
    account, actor, controller = context
    _, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    attacker = Actor("tenant-b", frozenset({"acct-synthetic"}))
    result = controller.confirm(
        account, attacker, session_id="session-a", offer_handle=handle, decision="accept"
    )
    assert result.reason == "unauthorized"
    assert controller.simulator.outcomes == {}


def test_decline_consumes_offer_without_mutation(context):
    account, actor, controller = context
    _, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    result = controller.confirm(
        account, actor, session_id="session-a", offer_handle=handle, decision="decline"
    )
    assert result.reason == "offer_declined"
    assert handle not in controller.pending
    assert controller.simulator.outcomes == {}


@pytest.mark.parametrize("amount", ["0", "19", "NaN", "Infinity"])
def test_ineligible_offer_never_creates_handle(context, amount):
    account, actor, controller = context
    result, handle = controller.propose(
        account, actor, session_id="session-a", amount=Decimal(amount)
    )
    assert result.outcome == "escalated"
    assert handle is None
    assert controller.pending == {}


@pytest.mark.parametrize("session_id", ["", " ", "\t"])
def test_blank_session_rejected(context, session_id):
    account, actor, controller = context
    result, handle = controller.propose(
        account, actor, session_id=session_id, amount=Decimal(10)
    )
    assert result.reason == "invalid_session"
    assert handle is None


def test_unknown_confirmation_decision_is_fail_closed(context):
    account, actor, controller = context
    _, handle = controller.propose(account, actor, session_id="session-a", amount=Decimal(10))
    result = controller.confirm(
        account, actor, session_id="session-a", offer_handle=handle, decision="maybe"
    )
    assert result.reason == "invalid_decision"
    assert handle in controller.pending
    assert controller.simulator.outcomes == {}
