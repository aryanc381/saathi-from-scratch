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
# A result with a missing field means the index is wrong, so it raises 503.
def as_chunk(source_id: str, row: dict) -> dict:
    if None in (source_id, row["clause_id"], row["version"], row["product"], row["text"]):
        raise ApiError(503, "search_misconfigured", "A search result is missing a field")
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


# Azure: embeds the query with the Foundry embedding model, then runs a hybrid (keywords + vector) semantic search.
def azure_search(settings: Settings, query: str, products: list[str], k: int) -> list[dict]:
    openai, search = settings.openai, settings.search
    joined_products = ",".join(products).replace("'", "''")  # a quote inside the filter text is doubled
    embed_url = f"{openai.endpoint.rstrip('/')}/openai/deployments/{openai.embed_deployment}/embeddings"
    embedding = post_json(embed_url, {"api-key": openai.api_key}, {"input": query}, {"api-version": OPENAI_API_VERSION})
    body = {
        "search": query,
        "vectorQueries": [{"kind": "vector", "vector": embedding["data"][0]["embedding"], "fields": "vector", "k": k}],
        "filter": f"search.in(product, '{joined_products}', ',')",
        "queryType": "semantic",
        "semanticConfiguration": "default",
        "select": "doc,clause_id,version,product,text",
        "top": k,
    }
    url = f"{search.endpoint.rstrip('/')}/indexes/{search.index_name}/docs/search"
    reply = post_json(url, {"api-key": search.admin_key}, body, {"api-version": SEARCH_API_VERSION})
    return [as_chunk(hit["doc"], hit) for hit in reply["value"]]


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
