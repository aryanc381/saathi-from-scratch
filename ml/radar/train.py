"""Responsible for training the Renewal Radar model on data/seed/csv/radar.csv and saving it to ml/artifacts/radar.

Run from the repo root: python -m ml.radar.train
"""
import csv
from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml.radar.score import FEATURES

ROOT = Path(__file__).resolve().parents[2]
CSV_FILE = ROOT / "data" / "seed" / "csv" / "radar.csv"
MODEL_FILE = ROOT / "ml" / "artifacts" / "radar" / "model.joblib"


# Reads radar.csv and returns the feature values and the renewed flag (0 or 1) of every row.
def read_rows() -> tuple[list[list[float]], list[int]]:
    with CSV_FILE.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [[float(row[name]) for name in FEATURES] for row in rows], [int(row["renewed"]) for row in rows]


# Trains on 80% of the rows, prints ROC-AUC on the other 20%, and saves the model.
def main():
    values, renewed = read_rows()
    train_x, test_x, train_y, test_y = train_test_split(values, renewed, test_size=0.2, random_state=42)
    # Scaling puts every feature on the same range, so the learned weights can be compared with each other.
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(train_x, train_y)
    print(f"test ROC-AUC: {roc_auc_score(test_y, model.predict_proba(test_x)[:, 1]):.3f}")

    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_FILE)
    print(f"saved {MODEL_FILE}")


if __name__ == "__main__":
    main()
