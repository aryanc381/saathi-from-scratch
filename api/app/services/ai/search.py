"""Responsible for finding policy clauses. RETRIEVER=local searches data/docs; azure uses AI Search."""
import json
import re
from functools import lru_cache
from pathlib import Path

from app.config import Settings
from app.models.errors import ApiError
from app.services.ai.client import OPENAI_API_VERSION, post_json

SEARCH_API_VERSION = "2024-07-01"
TOP_K = 5
CANDIDATES = TOP_K * 3  # Azure returns this many results; the product filter then keeps the best TOP_K
FILLER_WORDS = {"what", "does", "this", "that", "with", "from", "have", "under", "about", "which", "when", "will"}
MANIFEST = Path(__file__).resolve().parents[4] / "data" / "docs" / "json" / "manifest.json"  # repo root / data / ...


# Reads the clause list (with text) once.
@lru_cache
def load_clauses() -> list[dict]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


# Returns the words of four or more letters, lowercased, without common filler words.
def words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{4,}", text.lower())) - FILLER_WORDS


# Builds one search result in the shape the rest of the API uses.
def as_chunk(source_id: str, row: dict) -> dict:
    return {
        "source_id": source_id,
        "clause_id": row["clause_id"],
        "version": row["version"],
        "product": row["product"],
        "text": row["text"],
    }


# Local mock: ranks the clauses of the allowed products by how many query words they share.
def local_search(query: str, products: list[str], k: int) -> list[dict]:
    query_words = words(query)
    scored = []
    for clause in load_clauses():
        if clause["product"] in products:
            overlap = len(query_words & words(clause["title"] + " " + clause["text"]))
            if overlap > 0:
                scored.append((overlap, clause))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [as_chunk(clause["file"], clause) for _, clause in scored[:k]]


# Reads the clause id, product and version of an AI Search result. The file name gives the first two
# (health-silver-01.pdf is clause HEALTH-SILVER-01 of the health product), and the clause text gives the version
# ("Clause HEALTH-SILVER-01 (v1)"). A result that does not follow this is an index problem, so it raises 503.
def read_hit(hit: dict) -> dict:
    if hit["doc"] is None or hit["text"] is None:
        raise ApiError(503, "search_misconfigured", "A search result is missing its file name or text")
    version = re.search(r"\((v\d+)\)", hit["text"])
    if version is None:
        raise ApiError(503, "search_misconfigured", "A search result has no version")
    clause_id = hit["doc"].removesuffix(".pdf").upper()
    return {
        "clause_id": clause_id,
        "product": clause_id.split("-")[0].lower(),
        "version": version.group(1),
        "text": hit["text"],
    }


# Azure: embeds the query with the Foundry embedding model, then runs a hybrid (keywords + vector) semantic search.
# The product limit is applied here in code, after the search and before anything reaches the model.
def azure_search(settings: Settings, query: str, products: list[str], k: int) -> list[dict]:
    openai, search = settings.openai, settings.search
    embed_url = f"{openai.endpoint.rstrip('/')}/openai/deployments/{openai.embed_deployment}/embeddings"
    embedding = post_json(embed_url, {"api-key": openai.api_key}, {"input": query}, {"api-version": OPENAI_API_VERSION})
    body = {
        "search": query,
        "vectorQueries": [
            {"kind": "vector", "vector": embedding["data"][0]["embedding"], "fields": "vector", "k": CANDIDATES}
        ],
        "queryType": "semantic",
        "semanticConfiguration": "default",
        "select": "doc,text",
        "top": CANDIDATES,
    }
    url = f"{search.endpoint.rstrip('/')}/indexes/{search.index_name}/docs/search"
    reply = post_json(url, {"api-key": search.admin_key}, body, {"api-version": SEARCH_API_VERSION})
    chunks = [as_chunk(hit["doc"], read_hit(hit)) for hit in reply["value"]]
    return [chunk for chunk in chunks if chunk["product"] in products][:k]


# Returns the best clauses for a query, limited to the given products. No products means nothing may be searched.
def retrieve(settings: Settings, query: str, products: list[str], k: int) -> list[dict]:
    if not products:
        return []
    if settings.retriever == "local":
        return local_search(query, products, k)
    return azure_search(settings, query, products, k)


# Turns clauses into the numbered lines a prompt uses, so the model can cite them as [S1], [S2], ...
def format_sources(chunks: list[dict]) -> str:
    return "\n".join(f"[S{number}] {chunk['text']}" for number, chunk in enumerate(chunks, start=1))
