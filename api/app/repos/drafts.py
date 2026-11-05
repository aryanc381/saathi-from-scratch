"""Responsible for reading and writing renewal drafts."""
import json

from app.repos.db import Connection, Row, execute, fetch_all, fetch_one

DRAFT_COLUMNS = "draft_id, customer_id, agent_id, text, citations, status, approved_by"


# Turns the stored citations JSON text into a list.
def with_citations(row: Row) -> Row:
    row["citations"] = json.loads(row["citations"])
    return row


# Creates a PENDING draft. citations is a list of dicts.
def create(db: Connection, draft_id: str, customer_id: str, agent_id: str, text: str, citations: list[dict]) -> None:
    execute(
        db,
        "INSERT INTO drafts (draft_id, customer_id, agent_id, text, citations, status) "
        "VALUES (?, ?, ?, ?, ?, 'PENDING')",
        draft_id, customer_id, agent_id, text, json.dumps(citations),
    )


# Returns one draft, or None.
def get(db: Connection, draft_id: str) -> Row | None:
    row = fetch_one(db, f"SELECT {DRAFT_COLUMNS} FROM drafts WHERE draft_id = ?", draft_id)
    if row is None:
        return None
    return with_citations(row)


# Returns every draft with the given status, newest first.
def list_by_status(db: Connection, status: str) -> list[Row]:
    rows = fetch_all(db, f"SELECT {DRAFT_COLUMNS} FROM drafts WHERE status = ? ORDER BY ts DESC", status)
    return [with_citations(row) for row in rows]


# Approves a draft only if it is still PENDING. Returns how many rows changed (0 or 1).
def mark_approved(db: Connection, draft_id: str, approved_by: str) -> int:
    sql = "UPDATE drafts SET status = 'APPROVED', approved_by = ? WHERE draft_id = ? AND status = 'PENDING'"
    return execute(db, sql, approved_by, draft_id)


# Marks a draft sent only if it is still APPROVED. Returns how many rows changed (0 or 1).
def mark_sent(db: Connection, draft_id: str) -> int:
    return execute(db, "UPDATE drafts SET status = 'SENT' WHERE draft_id = ? AND status = 'APPROVED'", draft_id)


# Returns how many drafts there are per status.
def count_by_status(db: Connection) -> list[Row]:
    return fetch_all(db, "SELECT status, COUNT(*) AS total FROM drafts GROUP BY status")
