"""Responsible for a simple limit on how often one agent may do something that costs money, like asking the LLM."""
import threading
import time
from collections import deque

from app.models.errors import ApiError

lock = threading.Lock()
recent_calls: dict[tuple[str, str], deque] = {}


# Raises 429 when this agent already made max_calls calls of this kind in the last window_seconds.
# The counts live in this process only, so they reset when the app restarts.
def check(agent_id: str, kind: str, max_calls: int, window_seconds: int) -> None:
    now = time.monotonic()
    with lock:
        calls = recent_calls.setdefault((agent_id, kind), deque())
        while calls and now - calls[0] > window_seconds:
            calls.popleft()  # forget calls that are older than the window
        if len(calls) >= max_calls:
            raise ApiError(429, "rate_limited", "Too many requests. Wait a moment and try again.")
        calls.append(now)
