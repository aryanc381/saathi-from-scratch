"""Responsible for reading agents from the agents table."""
from app.repos.db import Connection, Row, fetch_one


# Returns one agent row (including the passcode hash), or None.
def get(db: Connection, agent_id: str) -> Row | None:
    sql = "SELECT agent_id, name, role, products, passcode_hash FROM agents WHERE agent_id = ?"
    return fetch_one(db, sql, agent_id)
