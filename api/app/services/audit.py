"""Responsible for the tamper-evident audit log: every row stores a hash of the row before it."""
import hashlib
import json
from datetime import datetime, timezone

from app.repos import audit as audit_repo
from app.repos.db import Connection

GENESIS = "0" * 64


# Returns the sha256 hash of one audit row together with the hash of the row before it.
def compute_hash(prev_hash: str, ts: str, actor: str, event_type: str, payload: str) -> str:
    return hashlib.sha256(f"{prev_hash}|{ts}|{actor}|{event_type}|{payload}".encode("utf-8")).hexdigest()


# Appends one event. payload is a dict of IDs only, never raw personal data.
def log(db: Connection, actor: str, event_type: str, payload: dict) -> None:
    payload_text = json.dumps(payload, sort_keys=True)
    ts = datetime.now(timezone.utc).replace(tzinfo=None)  # the DATETIME2 column has no timezone
    # The last hash is read under a table lock that insert() releases when it commits.
    last = audit_repo.last(db)
    if last is None:
        prev_hash = GENESIS
    else:
        prev_hash = last["hash"]
    hash_value = compute_hash(prev_hash, ts.isoformat(), actor, event_type, payload_text)
    audit_repo.insert(db, ts, actor, event_type, payload_text, prev_hash, hash_value)


# Walks the whole log and returns the id of the first row that does not match its hash, if any.
def verify(db: Connection) -> dict:
    rows = audit_repo.all_in_order(db)
    prev_hash = GENESIS
    # Each row must point at the hash of the row before it, and its own hash must match its contents.
    for row in rows:
        expected = compute_hash(prev_hash, row["ts"].isoformat(), row["actor"], row["type"], row["payload"])
        if row["prev_hash"] != prev_hash or row["hash"] != expected:
            return {"valid": False, "broken_at": row["id"], "count": len(rows)}
        prev_hash = row["hash"]
    return {"valid": True, "broken_at": None, "count": len(rows)}
