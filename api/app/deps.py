"""Responsible for the things every route needs: settings, a database connection and the logged-in agent."""
from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings, load_settings
from app.models.auth import Agent
from app.models.errors import ApiError
from app.repos.db import Connection, connect
from app.services import auth


# Reads the settings once and reuses them.
@lru_cache
def get_settings() -> Settings:
    return load_settings()


AppSettings = Annotated[Settings, Depends(get_settings)]


# Opens one SQL connection per request and closes it afterwards.
def get_db(settings: AppSettings) -> Iterator[Connection]:
    db = connect(settings.sql_connection_string)
    try:
        yield db
    finally:
        db.close()


Db = Annotated[Connection, Depends(get_db)]


# Returns the agent named by the "Authorization: Bearer <token>" header, or raises 401.
def current_agent(request: Request, db: Db, settings: AppSettings) -> Agent:
    header = request.headers.get("Authorization")
    if header is None or not header.startswith("Bearer "):
        raise ApiError(401, "missing_token", "Log in first")
    return auth.agent_from_token(db, header.removeprefix("Bearer "), settings.jwt_secret)


CurrentAgent = Annotated[Agent, Depends(current_agent)]


# Returns the logged-in agent only if they are a supervisor, otherwise raises 403.
def current_supervisor(agent: CurrentAgent) -> Agent:
    if agent.role != "supervisor":
        raise ApiError(403, "forbidden", "Supervisors only")
    return agent


Supervisor = Annotated[Agent, Depends(current_supervisor)]
