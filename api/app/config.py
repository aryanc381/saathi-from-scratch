"""Responsible for reading the API settings from environment variables. A missing variable stops the app."""
import os
from dataclasses import dataclass


# The settings the API needs.
@dataclass
class Settings:
    jwt_secret: str
    sql_connection_string: str


# Reads every setting from the environment; os.environ[...] raises if one is missing.
def load_settings() -> Settings:
    return Settings(
        jwt_secret=os.environ["JWT_SECRET"],
        sql_connection_string=os.environ["SQL_CONNECTION_STRING"],
    )
