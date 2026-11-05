"""Responsible for answering intent requests on the Azure ML endpoint.

init loads the model once; run scores one request.

Request:  { "text": "when does my policy renew?" }
Response: { "label": "renewal", "confidence": 0.93 }
"""
import json
import os
import sys
from pathlib import Path

# The endpoint's code folder is ml/, so add it to the path to import intent.score.
sys.path.append(str(Path(__file__).resolve().parents[2]))
from intent.score import classify, load

model = None


# Runs once when the endpoint starts: finds the registered model file and loads it.
def init():
    global model
    model = load(next(Path(os.environ["AZUREML_MODEL_DIR"]).rglob("model.joblib")))


# Runs for every request: reads the question and returns its intent.
def run(raw_data):
    return classify(model, json.loads(raw_data)["text"])
