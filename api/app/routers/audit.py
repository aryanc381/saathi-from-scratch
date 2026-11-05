"""Responsible for the supervisor views of the audit log, the chain check and usage counts."""
from fastapi import APIRouter

from app.deps import Db, Supervisor
from app.models.audit import AuditEvent, Usage, VerifyResult
from app.repos import audit as audit_repo
from app.repos import drafts as draft_repo
from app.services import audit

router = APIRouter()

LIST_LIMIT = 200


# Lists the newest audit events. Supervisors only.
# req: token / res: [{ id, ts, actor, type, payload, hash }] / errors: 401, 403
@router.get("/audit", response_model=list[AuditEvent])
def list_events(supervisor: Supervisor, db: Db):
    return audit_repo.recent(db, LIST_LIMIT)


# Checks the whole audit chain. Supervisors only.
# req: token / res: { valid, broken_at, count } / errors: 401, 403
@router.get("/audit/verify", response_model=VerifyResult)
def verify_chain(supervisor: Supervisor, db: Db):
    return audit.verify(db)


# Counts chats, blocked chats and drafts per status. Supervisors only.
# "chat" and "chat_blocked" events are logged by Phase 4, so those two counts are 0 until then.
# req: token / res: { chats, blocked, drafts_by_status } / errors: 401, 403
@router.get("/usage", response_model=Usage)
def usage(supervisor: Supervisor, db: Db):
    # Start every status at 0 so a status with no drafts still appears.
    drafts_by_status = {"PENDING": 0, "APPROVED": 0, "SENT": 0}
    for row in draft_repo.count_by_status(db):
        drafts_by_status[row["status"]] = row["total"]
    return {
        "chats": audit_repo.count_type(db, "chat"),
        "blocked": audit_repo.count_type(db, "chat_blocked"),
        "drafts_by_status": drafts_by_status,
    }
