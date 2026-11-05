"""Responsible for login checks, tokens and deciding which customers an agent may see."""
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

import jwt

from app.models.auth import Agent
from app.models.errors import ApiError
from app.repos import agents as agent_repo
from app.repos import customers as customer_repo
from app.repos.db import Connection, Row

TOKEN_HOURS = 8


# Returns the sha256 hex hash of a passcode.
def hash_passcode(passcode: str) -> str:
    return hashlib.sha256(passcode.encode("utf-8")).hexdigest()


# Turns an agents table row into an Agent (the passcode hash is left out).
def agent_from_row(row: Row) -> Agent:
    return Agent(agent_id=row["agent_id"], name=row["name"], role=row["role"], products=json.loads(row["products"]))


# Returns the Agent when the passcode is right, otherwise None.
def check_passcode(db: Connection, agent_id: str, passcode: str) -> Agent | None:
    row = agent_repo.get(db, agent_id)
    if row is None:
        return None
    # compare_digest takes the same time however many characters match.
    if not hmac.compare_digest(hash_passcode(passcode), row["passcode_hash"]):
        return None
    return agent_from_row(row)


# Creates a signed login token that expires after TOKEN_HOURS.
def make_token(agent: Agent, secret: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": agent.agent_id, "exp": expires}, secret, algorithm="HS256")


# Returns the Agent a token belongs to, or raises 401.
def agent_from_token(db: Connection, token: str, secret: str) -> Agent:
    try:
        # exp and sub must be present, so a token without an expiry is rejected.
        claims = jwt.decode(token, secret, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.InvalidTokenError:
        raise ApiError(401, "invalid_token", "Log in again")
    row = agent_repo.get(db, claims["sub"])
    if row is None:
        raise ApiError(401, "invalid_token", "Log in again")
    return agent_from_row(row)


# Returns the policies this agent may see: all for a supervisor, otherwise only approved products.
def visible_policies(agent: Agent, policies: list[Row]) -> list[Row]:
    if agent.role == "supervisor":
        return policies
    return [p for p in policies if p["product"] in agent.products]


# A supervisor sees every customer. An agent sees a customer they own who has a visible policy.
def can_access(agent: Agent, customer: Row, policies: list[Row]) -> bool:
    if agent.role == "supervisor":
        return True
    if customer["agent_id"] != agent.agent_id:
        return False
    return len(visible_policies(agent, policies)) > 0


# Returns a customer and only the policies the agent may see, otherwise raises 404 or 403.
def load_customer(db: Connection, agent: Agent, customer_id: str) -> tuple[Row, list[Row]]:
    customer = customer_repo.get(db, customer_id)
    if customer is None:
        raise ApiError(404, "customer_not_found", "Customer not found")
    policies = customer_repo.policies_for(db, customer_id)
    if not can_access(agent, customer, policies):
        raise ApiError(403, "forbidden", "You cannot access this customer")
    return customer, visible_policies(agent, policies)
