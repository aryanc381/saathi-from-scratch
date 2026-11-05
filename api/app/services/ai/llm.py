"""Responsible for asking the GPT model for text. LLM_PROVIDER=mock gives a canned reply; azure calls Foundry."""
import re

from app.config import Settings
from app.models.errors import ApiError
from app.services.ai.client import OPENAI_API_VERSION, post_json


# A stand-in for GPT: a draft request gets its message back unchanged, a chat request gets source 1 as a cited answer.
def mock_reply(prompt: str) -> str:
    if "Message to rewrite:" in prompt:
        return prompt.split("Message to rewrite:", 1)[1].strip()
    match = re.search(r"\[S1\] (.+)", prompt)
    if match is None:
        return "NOT_FOUND"
    return match.group(1).split(". ")[0].rstrip(".") + " [S1]."


# Sends one system prompt and one user prompt to the model and returns its text. Temperature 0 keeps answers steady.
def generate(settings: Settings, system: str, prompt: str) -> str:
    if settings.llm_provider == "mock":
        return mock_reply(prompt)
    openai = settings.openai
    url = f"{openai.endpoint.rstrip('/')}/openai/deployments/{openai.chat_deployment}/chat/completions"
    body = {"messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}], "temperature": 0}
    reply = post_json(url, {"api-key": openai.api_key}, body, {"api-version": OPENAI_API_VERSION})
    text = reply["choices"][0]["message"]["content"]
    if text is None:  # the content filter can return no text
        raise ApiError(503, "llm_empty", "The model returned no answer")
    return text
