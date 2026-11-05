"""Responsible for registering the two trained models in the Azure ML workspace.

Run from the repo root after training: python ml/azureml/scripts/register.py
Needs AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP and AZURE_ML_WORKSPACE, and a signed-in Azure CLI (az login).
"""
import os
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.entities import Model
from azure.identity import DefaultAzureCredential

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts"
MODELS = {"intent-classifier": ARTIFACTS / "intent" / "model.joblib", "renewal-radar": ARTIFACTS / "radar" / "model.joblib"}


# Registers each trained model file under its name and prints the version Azure gave it.
def main():
    client = MLClient(
        DefaultAzureCredential(),
        os.environ["AZURE_SUBSCRIPTION_ID"],
        os.environ["AZURE_RESOURCE_GROUP"],
        os.environ["AZURE_ML_WORKSPACE"],
    )
    for name, path in MODELS.items():
        registered = client.models.create_or_update(Model(name=name, path=str(path), type="custom_model"))
        print(f"registered {registered.name} version {registered.version}")


if __name__ == "__main__":
    main()
