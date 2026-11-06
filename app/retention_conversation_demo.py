"""Local synthetic demonstration of a bounded two-turn retention resolution.

Run: python -m app.retention_conversation_demo
No model, network, customer account, payment or production service involved.
"""

import json
from decimal import Decimal

from app.retention_conversation import Request, resolve
from app.retention_simulator import Account, Actor, CreditSimulator


def main() -> None:
    account = Account("demo-tenant", "demo-account", Decimal(60), Decimal(18))
    actor = Actor("demo-tenant", frozenset({"demo-account"}))
    simulator = CreditSimulator()
    # Confirmation is an explicit separate input, never inferred from the model.
    proposed = resolve(account, actor, Request("billing_credit", Decimal(10)), simulator)
    confirmed = resolve(
        account,
        actor,
        Request("billing_credit", Decimal(10), confirmed=True, idempotency_key="demo-1"),
        simulator,
    )
    replay = resolve(
        account,
        actor,
        Request("billing_credit", Decimal(10), confirmed=True, idempotency_key="demo-1"),
        simulator,
    )
    output = {
        "scope": "synthetic deterministic local simulation, not a deployed AI agent",
        "proposed": proposed.outcome,
        "confirmed": confirmed.outcome,
        "replay": replay.outcome,
        "recorded_actions": len(simulator.outcomes),
        "trace": list(confirmed.trace),
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
