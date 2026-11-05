"""Responsible for working out what the agent is asking about.

ML_PROVIDER=local uses simple word rules; azure calls the intent endpoint.
"""
import re

from app.config import Settings
from app.services.ai.client import post_json

# Local stand-in for the trained model. The first rule whose word-start matches wins, so the order matters.
GREETING_STEMS = ["hello", "hey", "thank", "bye", "morning"]
MAX_GREETING_WORDS = 3  # a longer question is a real question, even if it starts with "thanks"
LOCAL_RULES = [
    ("draft_message", ["draft", "write", "message", "remind"]),
    ("claim", ["claim", "settle", "reject"]),
    ("premium", ["premium", "price", "cost", "instalment", "discount"]),
    ("renewal", ["renew", "grace", "lapse", "due"]),
]


# Picks an intent from the question's words. Anything that matches no rule is treated as a policy question.
def local_classify(text: str) -> dict:
    question_words = re.findall(r"[a-z]+", text.lower())
    is_short = len(question_words) <= MAX_GREETING_WORDS
    if is_short and any(word.startswith(stem) for word in question_words for stem in GREETING_STEMS):
        return {"label": "other", "confidence": 1.0}
    for label, stems in LOCAL_RULES:
        if any(word.startswith(stem) for word in question_words for stem in stems):
            return {"label": label, "confidence": 1.0}
    return {"label": "policy_info", "confidence": 0.5}


# Returns { label, confidence } for a question.
def classify(settings: Settings, text: str) -> dict:
    if settings.ml_provider == "local":
        return local_classify(text)
    headers = {"Authorization": f"Bearer {settings.ml.intent_key}"}
    reply = post_json(settings.ml.intent_url, headers, {"text": text}, {})
    return {"label": reply["label"], "confidence": reply["confidence"]}
