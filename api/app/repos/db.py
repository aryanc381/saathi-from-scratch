"""Responsible for opening the SQL connection and running queries. Every other repo file uses these helpers."""
from typing import Any

import pyodbc

Connection = pyodbc.Connection
Row = dict[str, Any]


# Opens a connection to Azure SQL.
def connect(connection_string: str) -> Connection:
    return pyodbc.connect(connection_string)


# Runs a SELECT and returns every row as a dict.
def fetch_all(db: Connection, sql: str, *params: Any) -> list[Row]:
    cursor = db.cursor()
    cursor.execute(sql, params)
    names = [column[0] for column in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


# Runs a SELECT and returns the first row as a dict, or None when there is no row.
def fetch_one(db: Connection, sql: str, *params: Any) -> Row | None:
    rows = fetch_all(db, sql, *params)
    if rows:
        return rows[0]
    return None


# Runs an INSERT or UPDATE, commits, and returns how many rows changed.
def execute(db: Connection, sql: str, *params: Any) -> int:
    cursor = db.cursor()
    cursor.execute(sql, params)
    db.commit()
    return cursor.rowcount
