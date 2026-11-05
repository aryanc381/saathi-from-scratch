"""Responsible for sending JSON to an Azure service and returning its reply. Every Azure call goes through here."""
import logging

import httpx

from app.models.errors import ApiError

OPENAI_API_VERSION = "2024-10-21"
TIMEOUT_SECONDS = 30
logger = logging.getLogger("saathi")


# Sends a JSON POST and returns the JSON reply. Any network or HTTP error becomes a 503, with no details for the client.
def post_json(url: str, headers: dict, body: dict, params: dict) -> dict:
    try:
        response = httpx.post(url, headers=headers, json=body, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPError as error:
        logger.warning("Azure call to %s failed: %s", url, error)  # the client only sees a plain 503
        raise ApiError(503, "service_unavailable", "An Azure service is unavailable")
    return response.json()
