"""Creates the Azure AI Search pipeline: index, Blob data source, skillset and indexer.

Run from the repo root: python data/seed/create_index.py
Needs AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_ADMIN_KEY, AZURE_SEARCH_INDEX_NAME, AZURE_STORAGE_CONNECTION_STRING,
AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and AZURE_OPENAI_EMBED_DEPLOYMENT.

Flow: PDFs in Blob -> indexer (images normalized) -> skillset (OCR, merge, split, embed) -> one index row per chunk.
Every PUT is idempotent, so re-running updates the definitions. Creating the indexer starts a run.
"""
import os

import httpx

API_VERSION = "2024-07-01"
EMBED_MODEL = "text-embedding-3-small"  # must match the embedding deployment created by infra/modules/foundry.bicep
EMBED_DIMENSIONS = 1536
CONTAINER = "policies"
DATA_SOURCE = "policies-ds"
SKILLSET = "policies-skillset"
INDEXER = "policies-indexer"


# Index with a vector field and a semantic configuration; chunk_id uses the keyword analyzer that index projections need.
def index_definition(name):
    return {
        "name": name,
        "fields": [
            {"name": "chunk_id", "type": "Edm.String", "key": True, "searchable": True, "analyzer": "keyword"},
            {"name": "parent_id", "type": "Edm.String", "filterable": True},
            {"name": "doc", "type": "Edm.String", "searchable": True, "filterable": True},
            {"name": "clause_id", "type": "Edm.String", "searchable": True, "filterable": True},
            {"name": "version", "type": "Edm.String", "filterable": True},
            {"name": "product", "type": "Edm.String", "filterable": True},
            {"name": "text", "type": "Edm.String", "searchable": True},
            {"name": "vector", "type": "Collection(Edm.Single)", "searchable": True, "dimensions": EMBED_DIMENSIONS, "vectorSearchProfile": "vector-profile"},
        ],
        "vectorSearch": {
            "algorithms": [{"name": "hnsw", "kind": "hnsw"}],
            "profiles": [{"name": "vector-profile", "algorithm": "hnsw"}],
        },
        "semantic": {
            "configurations": [{
                "name": "default",
                "prioritizedFields": {"titleField": {"fieldName": "doc"}, "prioritizedContentFields": [{"fieldName": "text"}]},
            }],
        },
    }


# Blob container holding the policy PDFs.
def data_source_definition(storage_connection_string):
    return {"name": DATA_SOURCE, "type": "azureblob", "credentials": {"connectionString": storage_connection_string}, "container": {"name": CONTAINER}}


# OCR for image content, merged into the text, split into chunks, then embedded; each chunk becomes one index row.
def skillset_definition(index_name, openai_endpoint, openai_key, embed_deployment):
    return {
        "name": SKILLSET,
        "skills": [
            {"@odata.type": "#Microsoft.Skills.Vision.OcrSkill", "context": "/document/normalized_images/*",
             "inputs": [{"name": "image", "source": "/document/normalized_images/*"}],
             "outputs": [{"name": "text", "targetName": "ocr_text"}]},
            {"@odata.type": "#Microsoft.Skills.Text.MergeSkill", "context": "/document",
             "inputs": [{"name": "text", "source": "/document/content"},
                        {"name": "itemsToInsert", "source": "/document/normalized_images/*/ocr_text"},
                        {"name": "offsets", "source": "/document/normalized_images/*/contentOffset"}],
             "outputs": [{"name": "mergedText", "targetName": "merged_text"}]},
            {"@odata.type": "#Microsoft.Skills.Text.SplitSkill", "context": "/document", "textSplitMode": "pages",
             "maximumPageLength": 2000, "pageOverlapLength": 200,
             "inputs": [{"name": "text", "source": "/document/merged_text"}],
             "outputs": [{"name": "textItems", "targetName": "pages"}]},
            {"@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill", "context": "/document/pages/*",
             "resourceUri": openai_endpoint, "apiKey": openai_key, "deploymentId": embed_deployment,
             "modelName": EMBED_MODEL, "dimensions": EMBED_DIMENSIONS,
             "inputs": [{"name": "text", "source": "/document/pages/*"}],
             "outputs": [{"name": "embedding", "targetName": "vector"}]},
        ],
        "cognitiveServices": {"@odata.type": "#Microsoft.Azure.Search.CognitiveServicesByKey", "key": openai_key},
        "indexProjections": {
            "selectors": [{
                "targetIndexName": index_name,
                "parentKeyFieldName": "parent_id",
                "sourceContext": "/document/pages/*",
                "mappings": [
                    {"name": "text", "source": "/document/pages/*"},
                    {"name": "vector", "source": "/document/pages/*/vector"},
                    {"name": "doc", "source": "/document/metadata_storage_name"},
                    {"name": "clause_id", "source": "/document/clause_id"},
                    {"name": "version", "source": "/document/version"},
                    {"name": "product", "source": "/document/product"},
                ],
            }],
            "parameters": {"projectionMode": "skipIndexingParentDocuments"},
        },
    }


# Indexer that reads the blobs, normalizes embedded images for OCR, and runs the skillset.
def indexer_definition(index_name):
    return {
        "name": INDEXER, "dataSourceName": DATA_SOURCE, "targetIndexName": index_name, "skillsetName": SKILLSET,
        "parameters": {"configuration": {"dataToExtract": "contentAndMetadata", "imageAction": "generateNormalizedImages"}},
    }


# Creates or updates one Search resource and fails loudly on any HTTP error.
def put(client, kind, name, body):
    response = client.put(f"/{kind}/{name}", params={"api-version": API_VERSION}, json=body)
    response.raise_for_status()
    print(f"{kind}/{name}: {response.status_code}")


# Creates the index, data source, skillset and indexer in that order.
def main():
    index_name = os.environ["AZURE_SEARCH_INDEX_NAME"]
    with httpx.Client(base_url=os.environ["AZURE_SEARCH_ENDPOINT"].rstrip("/"), headers={"api-key": os.environ["AZURE_SEARCH_ADMIN_KEY"]}, timeout=60) as client:
        put(client, "indexes", index_name, index_definition(index_name))
        put(client, "datasources", DATA_SOURCE, data_source_definition(os.environ["AZURE_STORAGE_CONNECTION_STRING"]))
        put(client, "skillsets", SKILLSET, skillset_definition(index_name, os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/"),
                                                              os.environ["AZURE_OPENAI_API_KEY"], os.environ["AZURE_OPENAI_EMBED_DEPLOYMENT"]))
        put(client, "indexers", INDEXER, indexer_definition(index_name))


if __name__ == "__main__":
    main()
