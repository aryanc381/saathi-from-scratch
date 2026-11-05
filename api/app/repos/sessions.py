"""Responsible for reading and writing chat sessions and their turns."""
import json

from app.repos.db import Connection, Row, execute, fetch_all, fetch_one


# Creates an empty session.
def create(db: Connection, session_id: str, agent_id: str, customer_id: str) -> None:
    execute(db, "INSERT INTO sessions (session_id, agent_id, customer_id) VALUES (?, ?, ?)", session_id, agent_id, customer_id)


# Returns one session row, or None.
def get(db: Connection, session_id: str) -> Row | None:
    return fetch_one(db, "SELECT session_id, agent_id, customer_id, summary FROM sessions WHERE session_id = ?", session_id)


# Adds one turn to a session. citations is a list of dicts.
def add_turn(db: Connection, session_id: str, role: str, text: str, citations: list[dict]) -> None:
    execute(db, "INSERT INTO turns (session_id, role, text, citations) VALUES (?, ?, ?, ?)", session_id, role, text, json.dumps(citations))


# Returns the latest turns of a session, oldest first.
def last_turns(db: Connection, session_id: str, limit: int) -> list[Row]:
    rows = fetch_all(
        db,
        "SELECT TOP (?) role, text, citations, ts FROM turns WHERE session_id = ? ORDER BY turn_id DESC",
        limit,
        session_id,
    )
    for row in rows:
        row["citations"] = json.loads(row["citations"])
    rows.reverse()
    return rows


# Saves the rolling summary of a session.
def set_summary(db: Connection, session_id: str, summary: str) -> None:
    execute(db, "UPDATE sessions SET summary = ? WHERE session_id = ?", summary, session_id)
