"""Responsible for reading the API settings from environment variables. A missing variable stops the app."""
import os
from dataclasses import dataclass, field


# The settings the API needs.
@dataclass
class Settings:
    jwt_secret: str = field(repr=False)  # repr=False keeps secrets out of logs
    sql_connection_string: str = field(repr=False)


# Reads every setting from the environment. A missing variable or a JWT secret under 32 characters raises.
def load_settings() -> Settings:
    settings = Settings(
        jwt_secret=os.environ["JWT_SECRET"],
        sql_connection_string=os.environ["SQL_CONNECTION_STRING"],
    )
    if len(settings.jwt_secret) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters")
    return settings
