"""Responsible for the draft shapes used when creating, approving and sending a renewal message."""
from typing import Literal

from pydantic import BaseModel, Field

from app.models.citation import Citation


# Body of POST /drafts.
class DraftCreate(BaseModel):
    customer_id: str = Field(min_length=1, max_length=16)


# A renewal message draft.
class Draft(BaseModel):
    draft_id: str
    customer_id: str
    agent_id: str
    text: str
    citations: list[Citation]
    status: Literal["PENDING", "APPROVED", "SENT"]
    approved_by: str | None


# Response of POST /drafts/{id}/approve.
class ApproveResult(BaseModel):
    draft_id: str
    status: Literal["APPROVED"]
    approved_by: str


# Response of POST /drafts/{id}/send. Nothing is really sent.
class SendResult(BaseModel):
    draft_id: str
    status: Literal["SIMULATED_SENT"]
