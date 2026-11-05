"""Responsible for loading the intent model and classifying one question. Also used by the Azure ML scoring script."""
import joblib


# Loads the saved intent model from a file.
def load(path):
    return joblib.load(path)


# Returns the most likely intent label and how confident the model is.
def classify(model, text: str) -> dict:
    probabilities = model.predict_proba([text])[0]
    best = probabilities.argmax()
    return {"label": str(model.classes_[best]), "confidence": float(probabilities[best])}


# Lets you try the saved model from the command line: python ml/intent/score.py "when does my policy renew?"
if __name__ == "__main__":
    import sys
    from pathlib import Path

    model_file = Path(__file__).resolve().parents[1] / "artifacts" / "intent" / "model.joblib"
    print(classify(load(model_file), sys.argv[1]))
