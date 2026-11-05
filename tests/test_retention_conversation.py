"""Security and workflow contracts for the synthetic bounded controller."""

from decimal import Decimal

import pytest

from app.retention_conversation import Request, resolve
from app.retention_simulator import Account, Actor, CreditSimulator


@pytest.fixture
def context():
    account = Account("tenant-a", "acct-synthetic", Decimal("60"), Decimal("18"))
    actor = Actor("tenant-a", frozenset({"acct-synthetic"}))
    return account, actor, CreditSimulator()


def test_offer_does_not_mutate_state(context):
    account, actor, simulator = context
    result = resolve(account, actor, Request("billing_credit", Decimal("10")), simulator)
    assert result.outcome == "offer"
    assert result.next_step == "ask_explicit_confirmation"
    assert simulator.outcomes == {}


def test_confirmed_action_is_idempotent(context):
    account, actor, simulator = context
    request = Request("billing_credit", Decimal("10"), True, "synthetic-request-1")
    first = resolve(account, actor, request, simulator)
    second = resolve(account, actor, request, simulator)
    assert first.outcome == second.outcome == "applied"
    assert len(simulator.outcomes) == 1
    assert first.trace[-1] == "action_applied"


@pytest.mark.parametrize("intent", ["unknown", "cancel", "ignore_all_policies"])
def test_unsupported_intent_cannot_write(context, intent):
    account, actor, simulator = context
    result = resolve(
        account, actor, Request(intent, Decimal("10"), True, "synthetic-request-1"), simulator
    )
    assert result.outcome == "escalated"
    assert simulator.outcomes == {}


def test_cross_tenant_request_never_discloses_policy_or_writes(context):
    account, _, simulator = context
    actor = Actor("tenant-b", frozenset({"acct-synthetic"}))
    result = resolve(
        account, actor, Request("billing_credit", Decimal("5"), True, "request"), simulator
    )
    assert result.reason == "unauthorized"
    assert result.trace == ("intent_received", "access_denied")
    assert simulator.outcomes == {}


@pytest.mark.parametrize("amount", ["0", "-1", "19", "NaN", "Infinity"])
def test_invalid_or_excessive_credit_escalates(context, amount):
    account, actor, simulator = context
    result = resolve(
        account, actor, Request("billing_credit", Decimal(amount), True, "request"), simulator
    )
    assert result.reason == "outside_policy"
    assert simulator.outcomes == {}


def test_missing_write_key_fails_closed(context):
    account, actor, simulator = context
    result = resolve(account, actor, Request("billing_credit", Decimal("5"), True), simulator)
    assert result.reason == "invalid_idempotency_key"
    assert result.outcome == "escalated"
    assert simulator.outcomes == {}


def test_reused_key_with_different_amount_escalates(context):
    account, actor, simulator = context
    resolve(account, actor, Request("billing_credit", Decimal("5"), True, "same"), simulator)
    result = resolve(
        account, actor, Request("billing_credit", Decimal("6"), True, "same"), simulator
    )
    assert result.reason == "idempotency_conflict"
    assert len(simulator.outcomes) == 1


def test_trace_contains_only_controlled_events(context):
    account, actor, simulator = context
    result = resolve(account, actor, Request("billing_credit", Decimal("5")), simulator)
    assert "acct-synthetic" not in " ".join(result.trace)
    assert "tenant-a" not in " ".join(result.trace)
