"""Responsible for the rules about renewal drafts: what the reminder says and when it may be sent."""
from app.repos.db import Row


# Builds the renewal reminder text from a fixed template. Phase 4 replaces this with an LLM answer that has citations.
def draft_text(customer: Row, policy: Row) -> str:
    return (
        f"Hi {customer['name']}, your {policy['product']} {policy['tier']} policy renews on {policy['renewal_date']}. "
        "Please reply if you would like to renew."
    )


# Returns why a draft may not be sent ("not_approved" or "consent_missing"), or None when it may be sent.
def send_block_reason(draft: Row, customer: Row) -> str | None:
    if draft["status"] != "APPROVED":
        return "not_approved"
    if not customer["consent"]:
        return "consent_missing"
    return None
