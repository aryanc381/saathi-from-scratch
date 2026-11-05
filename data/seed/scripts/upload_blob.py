"""Responsible for uploading the policy-clause PDFs to Blob Storage.

Run from the repo root: python data/seed/scripts/upload_blob.py
Needs AZURE_STORAGE_CONNECTION_STRING. The 'policies' container is created by infra/bicep/modules/storage.bicep.
"""
import json
import os
from pathlib import Path

from azure.storage.blob import BlobServiceClient

DOCS_DIR = Path(__file__).parent.parent.parent / "docs"  # data/docs
CONTAINER = "policies"


# Uploads every PDF listed in manifest.json, replacing any blob with the same name.
def upload_docs(container):
    manifest = json.loads((DOCS_DIR / "json" / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest:
        with (DOCS_DIR / "pdf" / entry["file"]).open("rb") as f:
            container.upload_blob(name=entry["file"], data=f, overwrite=True)
        print(f"uploaded {entry['file']}")


# Uploads the policy PDFs to the policies container.
def main():
    service = BlobServiceClient.from_connection_string(os.environ["AZURE_STORAGE_CONNECTION_STRING"])
    upload_docs(service.get_container_client(CONTAINER))


if __name__ == "__main__":
    main()
