"""Responsible for answering Renewal Radar requests on the Azure ML endpoint (init loads the model, run scores one request).

Request:  { "rows": [{ "customer_id", "days_to_renewal", "annual_premium_inr",
                       "interaction_count_90d", "days_since_last_interaction" }] }
Response: { "results": [{ "customer_id", "score", "top_factors" }] }
"""
import json
import os
import sys
from pathlib import Path

# The endpoint's code folder is ml/, so add it to the path to import radar.score.
sys.path.append(str(Path(__file__).resolve().parents[2]))
from radar.score import load, predict  # noqa: E402

model = None


# Runs once when the endpoint starts: finds the registered model file and loads it.
def init():
    global model
    model = load(next(Path(os.environ["AZUREML_MODEL_DIR"]).rglob("model.joblib")))


# Runs for every request: scores the customers in the request.
def run(raw_data):
    return {"results": predict(model, json.loads(raw_data)["rows"])}
