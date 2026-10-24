"""Log agent decisions for transparency and demo."""

from agent.db import log_decision as db_log_decision


def log_decision(decision: str, reason: str, expected: str, outcome: str = "") -> dict:
    """Append a decision to the agent's memory."""
    db_log_decision(decision, reason, expected, outcome)
    return {"status": "logged", "decision": decision}
