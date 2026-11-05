"""Responsible for logging an agent in."""
from fastapi import APIRouter

from app.deps import AppSettings, Db
from app.models.auth import LoginRequest, LoginResponse
from app.models.errors import ApiError
from app.services.access import audit, auth

router = APIRouter()


# Checks the agent id and passcode and returns a token. Every attempt is audited.
# req: { agent_id, passcode } / res: { token, name, role } / errors: 401
@router.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Db, settings: AppSettings):
    agent = auth.check_passcode(db, body.agent_id, body.passcode)
    if agent is None:
        audit.log(db, body.agent_id, "login_failed", {})
        raise ApiError(401, "invalid_login", "Wrong agent id or passcode")
    audit.log(db, agent.agent_id, "login", {})
    return {"token": auth.make_token(agent, settings.jwt_secret), "name": agent.name, "role": agent.role}
