"""Reproducible synthetic retention policy evaluation; not a model benchmark."""

from dataclasses import dataclass
from decimal import Decimal

from app.retention_simulator import Account, Actor, CreditSimulator, assess_credit


@dataclass(frozen=True)
class Scenario:
    name: str
    monthly: str
    disputed: str
    active: bool
    same_tenant: bool
    account_access: bool
    amount: str
    confirmed: bool
    expected: str


SCENARIOS = (
    Scenario("eligible-small", "60", "5", True, True, True, "5", True, "applied"),
    Scenario("eligible-mid", "60", "18", True, True, True, "10", True, "applied"),
    Scenario("eligible-cap", "100", "50", True, True, True, "25", True, "applied"),
    Scenario("eligible-exact", "60", "18", True, True, True, "18", True, "applied"),
    Scenario("eligible-cents", "60", "18", True, True, True, "0.01", True, "applied"),
    Scenario("cross-tenant", "60", "18", True, False, True, "5", True, "rejected"),
    Scenario("no-account-access", "60", "18", True, True, False, "5", True, "rejected"),
    Scenario("inactive", "60", "18", False, True, True, "5", True, "rejected"),
    Scenario("zero-monthly", "0", "18", True, True, True, "5", True, "rejected"),
    Scenario("negative-monthly", "-1", "18", True, True, True, "5", True, "rejected"),
    Scenario("zero-dispute", "60", "0", True, True, True, "5", True, "rejected"),
    Scenario("negative-dispute", "60", "-1", True, True, True, "5", True, "rejected"),
    Scenario("over-monthly", "60", "61", True, True, True, "5", True, "rejected"),
    Scenario("no-confirmation", "60", "18", True, True, True, "5", False, "rejected"),
    Scenario("zero-credit", "60", "18", True, True, True, "0", True, "rejected"),
    Scenario("negative-credit", "60", "18", True, True, True, "-1", True, "rejected"),
    Scenario("above-dispute", "60", "18", True, True, True, "19", True, "rejected"),
    Scenario("above-cap", "100", "50", True, True, True, "26", True, "rejected"),
    Scenario("nan-credit", "60", "18", True, True, True, "NaN", True, "rejected"),
    Scenario("infinite-credit", "60", "18", True, True, True, "Infinity", True, "rejected"),
    Scenario("nan-monthly", "NaN", "18", True, True, True, "5", True, "rejected"),
    Scenario("infinite-dispute", "60", "Infinity", True, True, True, "5", True, "rejected"),
    Scenario("negative-infinite-monthly", "-Infinity", "18", True, True, True, "5", True, "rejected"),
    Scenario("small-dispute-large-credit", "60", "0.50", True, True, True, "1", True, "rejected"),
)


def run_suite() -> dict[str, object]:
    """Evaluate independent scenarios; no customer data, model calls or network."""
    failures: list[str] = []
    for scenario in SCENARIOS:
        account = Account(
            "tenant-a" if scenario.same_tenant else "tenant-b",
            "acct-synthetic",
            Decimal(scenario.monthly),
            Decimal(scenario.disputed),
            active=scenario.active,
        )
        actor = Actor(
            "tenant-a",
            frozenset({"acct-synthetic"} if scenario.account_access else set()),
        )
        # Check the deterministic policy separately from the action simulator.
        decision = assess_credit(account, actor)
        result = CreditSimulator().apply(
            account,
            actor,
            Decimal(scenario.amount),
            confirmed=scenario.confirmed,
            idempotency_key=scenario.name,
        )
        if result.status != scenario.expected:
            failures.append(scenario.name)
        if result.status == "applied" and not decision.eligible:
            failures.append(scenario.name + ":unsafe_action")
    return {
        "suite": "synthetic_deterministic_retention_policy_v1",
        "scenario_count": len(SCENARIOS),
        "passed": len(SCENARIOS) - len({name.split(":")[0] for name in failures}),
        "failures": failures,
        "scope": "local deterministic policy/action simulation; no LLM or production outcomes",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(run_suite(), indent=2))
