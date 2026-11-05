"""Creates the Saathi schema in Azure SQL and loads the demo rows.

Run from the repo root: python data/seed/load_sql.py
Needs SQL_CONNECTION_STRING. Meant for a fresh database: it deletes the demo tables before loading,
so it fails if sessions, turns or drafts already point at those rows.
"""
import json
import os
import re
from pathlib import Path

import pyodbc

SEED_DIR = Path(__file__).parent

# table -> (seed file, columns) in dependency order; deletes run in reverse.
TABLES = {
    "agents": ("agents.json", ["agent_id", "name", "role", "products"]),
    "customers": ("customers.json", ["customer_id", "agent_id", "name", "phone", "language", "consent"]),
    "policies": ("policies.json", ["policy_id", "customer_id", "product", "tier", "annual_premium_inr", "renewal_date", "status"]),
    "interactions": ("interactions.json", ["interaction_id", "customer_id", "date", "channel", "text"]),
}


# Runs every GO-separated batch in schema.sql.
def create_schema(cursor):
    script = (SEED_DIR / "schema.sql").read_text(encoding="utf-8")
    batches = [b.strip() for b in re.split(r"^GO\s*$", script, flags=re.MULTILINE) if b.strip()]
    for batch in batches:
        cursor.execute(batch)


# Replaces the demo rows in dependency order.
def load_data(cursor):
    for table in reversed(TABLES):
        cursor.execute(f"DELETE FROM {table}")
    for table, (file, columns) in TABLES.items():
        rows = json.loads((SEED_DIR / file).read_text(encoding="utf-8"))
        for row in rows:
            if table == "agents":
                row["products"] = json.dumps(row["products"])
        values = [[row[c] for c in columns] for row in rows]
        marks = ", ".join("?" for _ in columns)
        cursor.executemany(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({marks})", values)
        print(f"{table}: {len(values)} rows")


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
