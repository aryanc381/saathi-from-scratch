"""Responsible for the chat request, the chat answer and one remembered turn."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.citation import Citation


# Body of POST /chat. Leave session_id out to start a new session.
class ChatRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=16)
    session_id: str | None = Field(default=None, max_length=36)
    question: str = Field(min_length=1, max_length=1000)


# What the agent is asking about, and how sure the model is.
class IntentResult(BaseModel):
    label: str
    confidence: float


# Response of POST /chat. When blocked is true, reason says why and the answer is a fixed refusal.
class ChatResponse(BaseModel):
    session_id: str | None
    answer: str
    citations: list[Citation]
    intent: IntentResult | None
    blocked: bool
    reason: str | None


# One remembered message of a session.
class Turn(BaseModel):
    role: str
    text: str
    citations: list[Citation]
    ts: datetime
