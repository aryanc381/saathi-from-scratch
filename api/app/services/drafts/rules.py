"""Responsible for the rule about when a renewal draft may be sent."""
from app.repos.db import Row


# Returns why a draft may not be sent ("not_approved" or "consent_missing"), or None when it may be sent.
def send_block_reason(draft: Row, customer: Row) -> str | None:
    if draft["status"] != "APPROVED":
        return "not_approved"
    if not customer["consent"]:
        return "consent_missing"
    return None
