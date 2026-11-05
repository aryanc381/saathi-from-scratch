"""Responsible for the audit log, chain check and usage shapes."""
from datetime import datetime

from pydantic import BaseModel


# One row of the audit log.
class AuditEvent(BaseModel):
    id: int
    ts: datetime
    actor: str
    type: str
    payload: str  # the stored JSON text, returned as is
    hash: str


# Result of checking the audit chain. broken_at is the id of the first bad row.
class VerifyResult(BaseModel):
    valid: bool
    broken_at: int | None
    count: int


# Counts shown on the supervisor console.
class Usage(BaseModel):
    chats: int
    blocked: int
    drafts_by_status: dict[str, int]
