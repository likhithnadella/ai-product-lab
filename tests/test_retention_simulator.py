from decimal import Decimal

import pytest

from app.retention_simulator import Account, Actor, CreditSimulator, assess_credit


@pytest.fixture
def account():
    return Account("tenant-a", "acct-001", Decimal("60.00"), Decimal("18.00"))


@pytest.fixture
def actor():
    return Actor("tenant-a", frozenset({"acct-001"}))


def test_eligible_credit_is_bounded(account, actor):
    decision = assess_credit(account, actor)
    assert decision.eligible
    assert decision.maximum_credit == Decimal("18.00")


@pytest.mark.parametrize(
    ("account_kwargs", "expected"),
    [
        ({"tenant_id": "tenant-b"}, "unauthorized"),
        ({"active": False}, "inactive"),
        ({"disputed_charge": Decimal("90.00")}, "requires_review"),
        ({"disputed_charge": Decimal("0.00")}, "invalid_amount"),
    ],
)
def test_policy_denials(account, actor, account_kwargs, expected):
    changed = {**account.__dict__, **account_kwargs}
    assert assess_credit(Account(**changed), actor).reason == expected


def test_account_authorization_is_independent_of_tenant(account):
    actor = Actor("tenant-a", frozenset({"other-account"}))
    assert assess_credit(account, actor).reason == "unauthorized"


def test_confirmation_required(account, actor):
    simulator = CreditSimulator()
    result = simulator.apply(
        account, actor, Decimal("5.00"), confirmed=False, idempotency_key="req-1"
    )
    assert result.reason == "confirmation_required"
    assert simulator.outcomes == {}


@pytest.mark.parametrize("amount", [Decimal(0), Decimal(-1), Decimal(19), Decimal("NaN")])
def test_invalid_amount_rejected(account, actor, amount):
    result = CreditSimulator().apply(
        account, actor, amount, confirmed=True, idempotency_key="req-1"
    )
    assert result.reason == "outside_policy"


def test_successful_action_replays_without_double_application(account, actor):
    simulator = CreditSimulator()
    first = simulator.apply(
        account, actor, Decimal("10.00"), confirmed=True, idempotency_key="req-1"
    )
    second = simulator.apply(
        account, actor, Decimal("10.00"), confirmed=True, idempotency_key="req-1"
    )
    assert first == second
    assert first.status == "applied"
    assert len(simulator.outcomes) == 1


def test_reusing_key_with_different_payload_is_rejected(account, actor):
    simulator = CreditSimulator()
    simulator.apply(account, actor, Decimal("5.00"), confirmed=True, idempotency_key="req-1")
    result = simulator.apply(
        account, actor, Decimal("6.00"), confirmed=True, idempotency_key="req-1"
    )
    assert result.reason == "idempotency_conflict"


def test_cross_tenant_attempt_never_applies(account, actor):
    other = Account("tenant-b", "acct-001", Decimal(60), Decimal(18))
    result = CreditSimulator().apply(
        other, actor, Decimal(5), confirmed=True, idempotency_key="req-1"
    )
    assert result.reason == "unauthorized"


def test_invalid_idempotency_key(account, actor):
    result = CreditSimulator().apply(
        account, actor, Decimal(5), confirmed=True, idempotency_key=""
    )
    assert result.reason == "invalid_idempotency_key"
