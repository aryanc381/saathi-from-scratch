"""Responsible for chat memory: the last few turns of a session plus a rolling summary."""
from uuid import uuid4

from app.models.auth import Agent
from app.models.errors import ApiError
from app.repos import sessions as session_repo
from app.repos.db import Connection

LAST_TURNS = 6


# Starts a new session for an agent and customer, and returns its id.
def start_session(db: Connection, agent_id: str, customer_id: str) -> str:
    session_id = str(uuid4())
    session_repo.create(db, session_id, agent_id, customer_id)
    return session_id


# Returns the rolling summary and last turns of a session. Raises 404, or 403 for another agent's session.
def load(db: Connection, agent: Agent, session_id: str) -> dict:
    session = session_repo.get(db, session_id)
    if session is None:
        raise ApiError(404, "session_not_found", "Session not found")
    if agent.role != "supervisor" and session["agent_id"] != agent.agent_id:
        raise ApiError(403, "forbidden", "This session belongs to another agent")
    return {
        "customer_id": session["customer_id"],
        "summary": session["summary"],
        "turns": session_repo.last_turns(db, session_id, LAST_TURNS),
    }


# Adds one turn to a session. citations is a list of dicts.
def append_turn(db: Connection, session_id: str, role: str, text: str, citations: list[dict]) -> None:
    session_repo.add_turn(db, session_id, role, text, citations)


# Saves the rolling summary. The summary text itself is written by the LLM in Phase 4.
def set_summary(db: Connection, session_id: str, summary: str) -> None:
    session_repo.set_summary(db, session_id, summary)
