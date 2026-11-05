"""Responsible for reading the API settings from environment variables. A missing variable stops the app."""
import os
from dataclasses import dataclass, field


# Where to reach Azure AI Foundry for GPT chat and embeddings.
@dataclass
class OpenAISettings:
    endpoint: str
    api_key: str = field(repr=False)  # repr=False keeps secrets out of logs
    chat_deployment: str
    embed_deployment: str


# Where to reach the Azure AI Search index.
@dataclass
class SearchSettings:
    endpoint: str
    admin_key: str = field(repr=False)
    index_name: str


# Where to reach the two Azure ML endpoints (intent and Renewal Radar).
@dataclass
class MlSettings:
    intent_url: str
    intent_key: str = field(repr=False)
    radar_url: str
    radar_key: str = field(repr=False)


# Everything the API needs. The Azure groups are None when no mode switch asks for them.
@dataclass
class Settings:
    jwt_secret: str = field(repr=False)
    sql_connection_string: str = field(repr=False)
    llm_provider: str
    retriever: str
    ml_provider: str
    openai: OpenAISettings | None
    search: SearchSettings | None
    ml: MlSettings | None


# Reads a mode switch and checks it is one of the allowed values.
def read_mode(name: str, allowed: tuple[str, ...]) -> str:
    value = os.environ[name]
    if value not in allowed:
        raise ValueError(f"{name} must be one of {allowed}")
    return value


# Reads the Foundry settings.
def read_openai() -> OpenAISettings:
    return OpenAISettings(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        chat_deployment=os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT"],
        embed_deployment=os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"],
    )


# Reads the AI Search settings.
def read_search() -> SearchSettings:
    return SearchSettings(
        endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        admin_key=os.environ["AZURE_SEARCH_ADMIN_KEY"],
        index_name=os.environ["AZURE_SEARCH_INDEX_NAME"],
    )


# Reads the Azure ML endpoint settings.
def read_ml() -> MlSettings:
    return MlSettings(
        intent_url=os.environ["INTENT_ENDPOINT_URL"],
        intent_key=os.environ["INTENT_ENDPOINT_KEY"],
        radar_url=os.environ["RADAR_ENDPOINT_URL"],
        radar_key=os.environ["RADAR_ENDPOINT_KEY"],
    )


# Reads every setting from the environment. A missing variable, a bad mode or a JWT secret under 32 characters raises.
# An Azure group is only read when a mode switch asks for it.
def load_settings() -> Settings:
    jwt_secret = os.environ["JWT_SECRET"]
    if len(jwt_secret) < 32:
        raise ValueError("JWT_SECRET must be at least 32 characters")
    llm_provider = read_mode("LLM_PROVIDER", ("mock", "azure"))
    retriever = read_mode("RETRIEVER", ("local", "azure"))
    ml_provider = read_mode("ML_PROVIDER", ("local", "azure"))

    # GPT chat and the search embeddings both live in the Foundry resource.
    needs_openai = "azure" in (llm_provider, retriever)
    return Settings(
        jwt_secret=jwt_secret,
        sql_connection_string=os.environ["SQL_CONNECTION_STRING"],
        llm_provider=llm_provider,
        retriever=retriever,
        ml_provider=ml_provider,
        openai=read_openai() if needs_openai else None,
        search=read_search() if retriever == "azure" else None,
        ml=read_ml() if ml_provider == "azure" else None,
    )
