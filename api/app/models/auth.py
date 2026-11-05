"""Responsible for the login request, login response and the logged-in agent."""
from typing import Literal

from pydantic import BaseModel, Field


# Body of POST /auth/login.
class LoginRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=16)
    passcode: str = Field(min_length=1, max_length=100)


# Response of POST /auth/login.
class LoginResponse(BaseModel):
    token: str
    name: str
    role: str


# The logged-in agent. products lists which products they may see.
class Agent(BaseModel):
    agent_id: str
    name: str
    role: Literal["agent", "supervisor"]
    products: list[str]
