"""Responsible for reading customers, their policies and their interactions."""
from app.repos.db import Connection, Row, fetch_all, fetch_one

CUSTOMER_COLUMNS = "customer_id, agent_id, name, phone, language, consent"


# Returns every customer.
def list_all(db: Connection) -> list[Row]:
    return fetch_all(db, f"SELECT {CUSTOMER_COLUMNS} FROM customers ORDER BY customer_id")


# Returns the customers owned by one agent.
def list_by_agent(db: Connection, agent_id: str) -> list[Row]:
    return fetch_all(db, f"SELECT {CUSTOMER_COLUMNS} FROM customers WHERE agent_id = ? ORDER BY customer_id", agent_id)


# Returns one customer row, or None.
def get(db: Connection, customer_id: str) -> Row | None:
    return fetch_one(db, f"SELECT {CUSTOMER_COLUMNS} FROM customers WHERE customer_id = ?", customer_id)


# Returns a customer's policies, soonest renewal first.
def policies_for(db: Connection, customer_id: str) -> list[Row]:
    return fetch_all(
        db,
        "SELECT policy_id, customer_id, product, tier, annual_premium_inr, renewal_date, status "
        "FROM policies WHERE customer_id = ? ORDER BY renewal_date",
        customer_id,
    )


# Returns a customer's interactions, newest first.
def interactions_for(db: Connection, customer_id: str) -> list[Row]:
    return fetch_all(
        db,
        "SELECT interaction_id, customer_id, [date], channel, [text] "
        "FROM interactions WHERE customer_id = ? ORDER BY [date] DESC",
        customer_id,
    )
