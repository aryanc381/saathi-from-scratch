"""Responsible for reading and appending rows of the audit_events table. Rows are never updated or deleted."""
from datetime import datetime

from app.repos.db import Connection, Row, execute, fetch_all, fetch_one


# Returns the newest audit row, or None. TABLOCKX locks the table until insert() commits, so two writers
# can never read the same last hash and fork the chain.
def last(db: Connection) -> Row | None:
    return fetch_one(db, "SELECT TOP 1 id, hash FROM audit_events WITH (TABLOCKX) ORDER BY id DESC")


# Appends one audit row and commits (this also releases the lock taken by last()).
def insert(
    db: Connection, ts: datetime, actor: str, event_type: str, payload: str, prev_hash: str, hash_value: str
) -> None:
    execute(
        db,
        "INSERT INTO audit_events (ts, actor, [type], payload, prev_hash, hash) VALUES (?, ?, ?, ?, ?, ?)",
        ts, actor, event_type, payload, prev_hash, hash_value,
    )


# Returns every audit row, oldest first, for checking the chain.
def all_in_order(db: Connection) -> list[Row]:
    return fetch_all(db, "SELECT id, ts, actor, [type], payload, prev_hash, hash FROM audit_events ORDER BY id")


# Returns the newest audit rows, newest first.
def recent(db: Connection, limit: int) -> list[Row]:
    sql = "SELECT TOP (?) id, ts, actor, [type] AS type, payload, hash FROM audit_events ORDER BY id DESC"
    return fetch_all(db, sql, limit)


# Returns how many audit rows have the given type.
def count_type(db: Connection, event_type: str) -> int:
    return fetch_one(db, "SELECT COUNT(*) AS total FROM audit_events WHERE [type] = ?", event_type)["total"]
