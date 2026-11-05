"""Responsible for creating, listing, approving and sending renewal drafts. Nothing is really sent."""
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter

from app.deps import AppSettings, CurrentAgent, Db, Supervisor
from app.models.draft import ApproveResult, Draft, DraftCreate, SendResult
from app.models.errors import ApiError
from app.repos import customers as customer_repo
from app.repos import drafts as draft_repo
from app.services.access import audit, auth, limits
from app.services.drafts import rules, writer

router = APIRouter()

DRAFTS_PER_MINUTE = 5


# Returns a draft the agent owns (a supervisor may use any draft), or raises 404 or 403.
def load_own_draft(db, agent, draft_id):
    draft = draft_repo.get(db, draft_id)
    if draft is None:
        raise ApiError(404, "draft_not_found", "Draft not found")
    if agent.role != "supervisor" and draft["agent_id"] != agent.agent_id:
        raise ApiError(403, "forbidden", "This draft belongs to another agent")
    return draft


# Creates a PENDING renewal draft for a customer the agent may access. The LLM polishes it and cites any policy rule.
# req: { customer_id } / res: draft / errors: 400, 401, 403, 404, 409, 429, 503
@router.post("/drafts", response_model=Draft, status_code=201)
def create_draft(body: DraftCreate, agent: CurrentAgent, db: Db, settings: AppSettings):
    limits.check(agent.agent_id, "draft", DRAFTS_PER_MINUTE, 60)
    customer, policies = auth.load_customer(db, agent, body.customer_id)
    if not policies:
        raise ApiError(409, "no_policy", "This customer has no policy to renew")
    draft_id = str(uuid4())
    text, citations = writer.write_draft(settings, customer, policies[0])  # policies holds only what this agent may see
    draft_repo.create(db, draft_id, customer["customer_id"], agent.agent_id, text, citations)
    audit.log(db, agent.agent_id, "draft_created", {"draft_id": draft_id, "customer_id": customer["customer_id"]})
    return draft_repo.get(db, draft_id)


# Lists the drafts with one status. Supervisors only.
# req: ?status=PENDING|APPROVED|SENT / res: [draft] / errors: 400, 401, 403
@router.get("/drafts", response_model=list[Draft])
def list_drafts(status: Literal["PENDING", "APPROVED", "SENT"], supervisor: Supervisor, db: Db):
    return draft_repo.list_by_status(db, status)


# Approves a PENDING draft. The owner or a supervisor may approve.
# req: token / res: { draft_id, status, approved_by } / errors: 401, 403, 404, 409
@router.post("/drafts/{draft_id}/approve", response_model=ApproveResult)
def approve_draft(draft_id: str, agent: CurrentAgent, db: Db):
    load_own_draft(db, agent, draft_id)
    # The UPDATE only changes a PENDING draft, so a draft cannot be approved twice.
    if draft_repo.mark_approved(db, draft_id, agent.agent_id) == 0:
        raise ApiError(409, "not_pending", "Only a pending draft can be approved")
    audit.log(db, agent.agent_id, "draft_approved", {"draft_id": draft_id})
    return {"draft_id": draft_id, "status": "APPROVED", "approved_by": agent.agent_id}


# "Sends" an APPROVED draft if the customer has given consent. The owner or a supervisor may send.
# req: token / res: { draft_id, status } / errors: 401, 403 (no consent), 404, 409 (not approved)
@router.post("/drafts/{draft_id}/send", response_model=SendResult)
def send_draft(draft_id: str, agent: CurrentAgent, db: Db):
    draft = load_own_draft(db, agent, draft_id)
    customer = customer_repo.get(db, draft["customer_id"])
    reason = rules.send_block_reason(draft, customer)
    if reason == "not_approved":
        raise ApiError(409, "not_approved", "Approve the draft before sending")
    if reason == "consent_missing":
        audit.log(db, agent.agent_id, "send_blocked", {"draft_id": draft_id, "reason": reason})
        raise ApiError(403, "consent_missing", "The customer has not given consent")
    # The UPDATE only changes an APPROVED draft, so two sends at once cannot both succeed.
    if draft_repo.mark_sent(db, draft_id) == 0:
        raise ApiError(409, "not_approved", "Approve the draft before sending")
    audit.log(db, agent.agent_id, "draft_sent", {"draft_id": draft_id})
    return {"draft_id": draft_id, "status": "SIMULATED_SENT"}
