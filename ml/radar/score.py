"""Responsible for the Renewal Radar features and for scoring customers. Also used by the Azure ML scoring script."""
import joblib

# The numbers the model reads for each customer, in this order.
FEATURES = ["days_to_renewal", "annual_premium_inr", "interaction_count_90d", "days_since_last_interaction"]
TOP_FACTORS = 2


# Loads the saved radar model from a file.
def load(path):
    return joblib.load(path)


# Scores each row (a dict with customer_id and every feature) and names the factors that moved the score most.
def predict(model, rows: list[dict]) -> list[dict]:
    values = [[row[name] for name in FEATURES] for row in rows]
    scores = model.predict_proba(values)[:, 1]
    scaler, classifier = model[0], model[1]
    # Each feature's push on the score = its standardized value times its learned weight.
    contributions = scaler.transform(values) * classifier.coef_[0]
    results = []
    for row, score, contribution in zip(rows, scores, contributions):
        ranked = sorted(range(len(FEATURES)), key=lambda i: abs(contribution[i]), reverse=True)
        top_factors = [FEATURES[i] for i in ranked[:TOP_FACTORS]]
        results.append({"customer_id": row["customer_id"], "score": float(score), "top_factors": top_factors})
    return results
