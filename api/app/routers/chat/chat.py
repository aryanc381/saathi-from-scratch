"""Responsible for asking a question about a customer and for reading back a session's remembered turns."""
from fastapi import APIRouter

from app.deps import AppSettings, CurrentAgent, Db
from app.models.chat import ChatRequest, ChatResponse, Turn
from app.orchestrator import pipeline
from app.services.chat import memory

router = APIRouter()


# Answers a question about a customer, with citations. A blocked question returns blocked=true with a reason.
# req: { customer_id, session_id?, question } / res: { session_id, answer, citations, intent, blocked, reason }
# errors: 400, 401, 403, 404, 429, 503
@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, agent: CurrentAgent, db: Db, settings: AppSettings):
    return pipeline.answer(db, settings, agent, body.customer_id, body.session_id, body.question)


# Returns the last remembered turns of one of the agent's sessions. A supervisor may read any session.
# req: token / res: [{ role, text, citations, ts }] / errors: 401, 403, 404
@router.get("/sessions/{session_id}", response_model=list[Turn])
def get_session(session_id: str, agent: CurrentAgent, db: Db):
    return memory.load(db, agent, session_id)["turns"]
