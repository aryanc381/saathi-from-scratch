"""Responsible for the Renewal Radar worklist: it scores the customers an agent may see who can still renew, best first.

ML_PROVIDER=local uses a simple formula as a stand-in for the trained model; azure calls the radar endpoint.
"""
import math
from datetime import date

from app.config import Settings
from app.models.auth import Agent
from app.repos import customers as customer_repo
from app.repos.db import Connection, Row
from app.services.access import auth
from app.services.ai.client import post_json
from app.services.customers import renewal

WORKLIST_SIZE = 10
RECENT_DAYS = 90
NO_CONTACT_DAYS = 365  # used for a customer with no interactions at all
CAN_RENEW = ("ACTIVE", "IN_GRACE")
TOP_FACTORS = 2


# Builds the model inputs for one customer from their policy and their interaction history.
def build_features(db: Connection, customer: Row, policy: Row) -> dict:
    today = date.today()
    interactions = customer_repo.interactions_for(db, customer["customer_id"])  # newest first
    recent = [i for i in interactions if (today - i["date"]).days <= RECENT_DAYS]
    if interactions:
        days_since_last = (today - interactions[0]["date"]).days
    else:
        days_since_last = NO_CONTACT_DAYS
    return {
        "customer_id": customer["customer_id"],
        "days_to_renewal": (policy["renewal_date"] - today).days,
        "annual_premium_inr": policy["annual_premium_inr"],
        "interaction_count_90d": len(recent),
        "days_since_last_interaction": days_since_last,
    }


# Local stand-in for the trained model: the same weights the training data was generated with.
def local_score(rows: list[dict]) -> list[dict]:
    results = []
    for row in rows:
        parts = {
            "interaction_count_90d": 0.35 * row["interaction_count_90d"],
            "days_since_last_interaction": -0.02 * row["days_since_last_interaction"],
            "annual_premium_inr": -0.000012 * (row["annual_premium_inr"] - 40000),
            "days_to_renewal": -0.03 * max(-row["days_to_renewal"], 0),
        }
        score = 1 / (1 + math.exp(-(0.6 + sum(parts.values()))))
        top_factors = sorted(parts, key=lambda name: abs(parts[name]), reverse=True)[:TOP_FACTORS]
        results.append({"customer_id": row["customer_id"], "score": score, "top_factors": top_factors})
    return results


# Scores the rows locally or on the Azure endpoint. Both return [{ customer_id, score, top_factors }].
def score_rows(settings: Settings, rows: list[dict]) -> list[dict]:
    if settings.ml_provider == "local":
        return local_score(rows)
    headers = {"Authorization": f"Bearer {settings.ml.radar_key}"}
    return post_json(settings.ml.radar_url, headers, {"rows": rows}, {})["results"]


# Returns the top customers this agent may see who can still renew, with their renewal score, best first.
def worklist(db: Connection, settings: Settings, agent: Agent) -> list[dict]:
    candidates = []
    for customer, policies in auth.visible_customers(db, agent):
        if policies and renewal.renewal_status(policies[0]) in CAN_RENEW:
            candidates.append((customer, policies[0]))
    if not candidates:
        return []
    rows = [build_features(db, customer, policy) for customer, policy in candidates]
    scores = {result["customer_id"]: result for result in score_rows(settings, rows)}
    results = [
        {
            "customer_id": customer["customer_id"],
            "name": customer["name"],
            "days_to_renewal": row["days_to_renewal"],
            "score": scores[customer["customer_id"]]["score"],
            "top_factors": scores[customer["customer_id"]]["top_factors"],
            "status": renewal.renewal_status(policy),
        }
        for (customer, policy), row in zip(candidates, rows)
    ]
    results.sort(key=lambda result: result["score"], reverse=True)
    return results[:WORKLIST_SIZE]
