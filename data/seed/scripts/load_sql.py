"""Responsible for creating the Saathi schema in Azure SQL and loading the demo rows.

Run from the repo root: python data/seed/scripts/load_sql.py
Needs SQL_CONNECTION_STRING. Meant for a fresh database: it deletes the demo rows first,
so it fails if sessions, turns or drafts already point at them.
"""
import json
import os
import re
from pathlib import Path

import pyodbc

SEED_DIR = Path(__file__).parent.parent  # data/seed


# Reads one JSON file from data/seed/json.
def read_json(file):
    return json.loads((SEED_DIR / "json" / file).read_text(encoding="utf-8"))


# Runs every GO-separated batch in schema.sql.
def create_schema(cursor):
    script = (SEED_DIR / "sql" / "schema.sql").read_text(encoding="utf-8")
    for batch in re.split(r"^GO\s*$", script, flags=re.MULTILINE):
        if batch.strip():
            cursor.execute(batch)


# Inserts the given columns of every row into one table.
def insert_rows(cursor, table, columns, rows):
    values = [[row[column] for column in columns] for row in rows]
    marks = ", ".join("?" for _ in columns)
    cursor.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({marks})", values)
    print(f"{table}: {len(values)} rows")


# Deletes the old demo rows, then inserts the new ones, parents before children.
def load_data(cursor):
    for table in ["interactions", "policies", "customers", "agents"]:
        cursor.execute(f"DELETE FROM {table}")

    agents = read_json("agents.json")
    for agent in agents:
        agent["products"] = json.dumps(agent["products"])

    insert_rows(cursor, "agents", ["agent_id", "name", "role", "products", "passcode_hash"], agents)
    insert_rows(cursor, "customers", ["customer_id", "agent_id", "name", "phone", "language", "consent"], read_json("customers.json"))
    insert_rows(cursor, "policies", ["policy_id", "customer_id", "product", "tier", "annual_premium_inr", "renewal_date", "status"], read_json("policies.json"))
    insert_rows(cursor, "interactions", ["interaction_id", "customer_id", "date", "channel", "text"], read_json("interactions.json"))


# Creates the schema and loads the demo rows in one transaction.
def main():
    connection = pyodbc.connect(os.environ["SQL_CONNECTION_STRING"])
    cursor = connection.cursor()
    create_schema(cursor)
    load_data(cursor)
    connection.commit()
    connection.close()


if __name__ == "__main__":
    main()
