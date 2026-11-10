"""Additional tenant-quota safety cases for the synthetic retention pilot."""

from decimal import Decimal

from app.retention_sessions import SessionRetentionController
from app.retention_simulator import Account, Actor


def subject(tenant_id: str):
    return (
        Account(tenant_id, "acct-synthetic", Decimal(60), Decimal(18)),
        Actor(tenant_id, frozenset({"acct-synthetic"})),
    )


def test_global_capacity_remains_an_independent_limit():
    controller = SessionRetentionController(
        max_pending_offers=1, max_pending_offers_per_tenant=2
    )
    a, actor_a = subject("tenant-a")
    b, actor_b = subject("tenant-b")
    _, first = controller.propose(a, actor_a, session_id="s1", amount=Decimal(10))
    denied, second = controller.propose(
        b, actor_b, session_id="s2", amount=Decimal(10)
    )
    assert first is not None
    assert denied.reason == "offer_capacity_reached"
    assert second is None
    assert controller.simulator.outcomes == {}


def test_unauthorized_attempt_does_not_consume_tenant_capacity():
    controller = SessionRetentionController(max_pending_offers_per_tenant=1)
    account, actor = subject("tenant-a")
    wrong_actor = Actor("tenant-b", frozenset({"acct-synthetic"}))
    denied, handle = controller.propose(
        account, wrong_actor, session_id="s1", amount=Decimal(10)
    )
    assert denied.outcome != "offer"
    assert handle is None
    offered, valid_handle = controller.propose(
        account, actor, session_id="s2", amount=Decimal(10)
    )
    assert offered.outcome == "offer"
    assert valid_handle is not None


def test_unauthorized_confirmation_does_not_release_other_tenant_quota():
    controller = SessionRetentionController(max_pending_offers_per_tenant=1)
    account, actor = subject("tenant-a")
    other, other_actor = subject("tenant-b")
    _, handle = controller.propose(
        account, actor, session_id="s1", amount=Decimal(10)
    )
    response = controller.confirm(
        other, other_actor, session_id="s1", offer_handle=handle, decision="decline"
    )
    assert response.reason == "unauthorized"
    denied, new = controller.propose(
        account, actor, session_id="s2", amount=Decimal(10)
    )
    assert denied.reason == "tenant_offer_capacity_reached"
    assert new is None
    assert handle in controller.pending
