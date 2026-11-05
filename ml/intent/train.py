"""Responsible for training the intent classifier on data/seed/csv and saving it to ml/artifacts/intent.

Run from the repo root: python -m ml.intent.train
"""
import csv
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import make_pipeline

ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = ROOT / "data" / "seed" / "csv"
MODEL_FILE = ROOT / "ml" / "artifacts" / "intent" / "model.joblib"


# Reads one intent CSV and returns its texts and labels.
def read_split(name: str) -> tuple[list[str], list[str]]:
    with (CSV_DIR / f"intent_{name}.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return [row["text"] for row in rows], [row["label"] for row in rows]


# Trains on the train split, prints macro-F1 on dev and test, and saves the model.
def main():
    train_texts, train_labels = read_split("train")
    # TF-IDF turns each question into word weights; logistic regression picks the label from them.
    model = make_pipeline(TfidfVectorizer(ngram_range=(1, 2)), LogisticRegression(max_iter=1000))
    model.fit(train_texts, train_labels)

    for name in ("dev", "test"):
        texts, labels = read_split(name)
        print(f"{name} macro-F1: {f1_score(labels, model.predict(texts), average='macro'):.3f}")

    MODEL_FILE.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_FILE)
    print(f"saved {MODEL_FILE}")


if __name__ == "__main__":
    main()
