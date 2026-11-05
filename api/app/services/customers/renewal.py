"""Responsible for working out where a customer's policies stand in the renewal cycle."""
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
