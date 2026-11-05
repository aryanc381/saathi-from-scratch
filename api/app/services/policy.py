"""Responsible for the business rules about renewals and sending a draft."""
from datetime import date

from app.repos.db import Row

GRACE_DAYS = 30


# Returns the renewal state of one policy: ACTIVE, IN_GRACE, LAPSED or CANCELLED.
def renewal_status(policy: Row) -> str:
    if policy["status"] == "CANCELLED":
        return "CANCELLED"
    days_left = (policy["renewal_date"] - date.today()).days
    if days_left >= 0:
        return "ACTIVE"
    if days_left >= -GRACE_DAYS:
        return "IN_GRACE"
    return "LAPSED"


# Returns the renewal state of a customer, taken from their soonest-renewing policy.
def customer_renewal_status(policies: list[Row]) -> str:
    if not policies:
        return "NO_POLICY"
    return renewal_status(policies[0])


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
