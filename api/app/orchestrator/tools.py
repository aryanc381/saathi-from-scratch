"""Responsible for the one tool the agent may call, search_knowledge_base: its JSON schema, allowlist and call limit."""
import logging

from app.config import Settings
from app.models.errors import ApiError
from app.services.ai import search

MAX_CALLS = 3
logger = logging.getLogger("saathi.tools")

# The tool as a model sees it: a name, what it does, and a JSON schema for its arguments.
TOOLS = [
    {
        "name": "search_knowledge_base",
        "description": "Search the insurance policy clauses and return the best matches.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "products": {"type": "array", "items": {"type": "string"}}},
            "required": ["query", "products"],
        },
    }
]


# Runs one allowed tool. Raises if the tool is unknown or this request has already used its MAX_CALLS.
def run_tool(settings: Settings, name: str, arguments: dict, calls_made: int) -> list[dict]:
    if name not in [tool["name"] for tool in TOOLS]:
        raise ApiError(400, "unknown_tool", "That tool is not allowed")
    if calls_made >= MAX_CALLS:
        raise ApiError(400, "too_many_tool_calls", "Too many tool calls in one request")
    logger.info("tool call: %s", name)  # only the name is logged, never the question text
    return search.retrieve(settings, arguments["query"], arguments["products"], search.TOP_K)
