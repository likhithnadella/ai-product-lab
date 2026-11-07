"""Run a synthetic, session-bound two-turn retention demo.

Run: python -m app.retention_sessions_demo
No real customer records, credentials, billing APIs, or LLM calls.
"""

from decimal import Decimal

from app.retention_sessions import SessionRetentionController
from app.retention_simulator import Account, Actor


def main() -> None:
    account = Account("tenant-demo", "synthetic-account", Decimal(60), Decimal(18))
    actor = Actor("tenant-demo", frozenset({"synthetic-account"}))
    controller = SessionRetentionController()
    proposal, handle = controller.propose(
        account, actor, session_id="trusted-demo-session", amount=Decimal(10)
    )
    print(f"proposal={proposal.outcome} reason={proposal.reason}")
    if handle is None:
        return
    confirmation = controller.confirm(
        account,
        actor,
        session_id="trusted-demo-session",
        offer_handle=handle,
        decision="accept",
    )
    print(f"confirmation={confirmation.outcome} reason={confirmation.reason}")
    print(f"simulated_writes={len(controller.simulator.outcomes)}")


if __name__ == "__main__":
    main()
