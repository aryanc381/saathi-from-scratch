"""Responsible for creating the two Azure ML online endpoints (intent and radar) and deploying the registered models.

Run from the repo root after register.py: python ml/azureml/scripts/deploy.py
Needs AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP and AZURE_ML_WORKSPACE, and a signed-in Azure CLI (az login).
Endpoints bill while they run. Delete them after the demo.
"""
import os
from pathlib import Path

from azure.ai.ml import MLClient
from azure.ai.ml.entities import (
    CodeConfiguration,
    Environment,
    ManagedOnlineDeployment,
    ManagedOnlineEndpoint,
)
from azure.identity import DefaultAzureCredential

ML_DIR = Path(__file__).resolve().parents[2]
BASE_IMAGE = "mcr.microsoft.com/azureml/openmpi4.1.2-ubuntu20.04:latest"
INSTANCE_TYPE = "Standard_D2a_v4"
DEPLOYMENT = "blue"

# endpoint name -> (registered model, scoring script inside ml/)
ENDPOINTS = {
    "saathi-intent-ep": ("intent-classifier", "azureml/scripts/score_intent.py"),
    "saathi-radar-ep": ("renewal-radar", "azureml/scripts/score_radar.py"),
}


# Creates one key-protected endpoint, deploys the model to it on one small instance, and sends all traffic there.
def deploy(client: MLClient, endpoint_name: str, model_name: str, scoring_script: str):
    client.online_endpoints.begin_create_or_update(ManagedOnlineEndpoint(name=endpoint_name, auth_mode="key")).result()
    deployment = ManagedOnlineDeployment(
        name=DEPLOYMENT,
        endpoint_name=endpoint_name,
        model=f"{model_name}@latest",
        code_configuration=CodeConfiguration(code=str(ML_DIR), scoring_script=scoring_script),
        environment=Environment(image=BASE_IMAGE, conda_file=str(ML_DIR / "azureml" / "config" / "conda.yml")),
        instance_type=INSTANCE_TYPE,
        instance_count=1,
    )
    client.online_deployments.begin_create_or_update(deployment).result()
    endpoint = client.online_endpoints.get(endpoint_name)
    endpoint.traffic = {DEPLOYMENT: 100}
    client.online_endpoints.begin_create_or_update(endpoint).result()
    print(f"{endpoint_name}: {client.online_endpoints.get(endpoint_name).scoring_uri}")


# Deploys every endpoint. The key is not printed: get it with `az ml online-endpoint get-credentials -n <endpoint>`.
def main():
    client = MLClient(
        DefaultAzureCredential(),
        os.environ["AZURE_SUBSCRIPTION_ID"],
        os.environ["AZURE_RESOURCE_GROUP"],
        os.environ["AZURE_ML_WORKSPACE"],
    )
    for endpoint_name, (model_name, scoring_script) in ENDPOINTS.items():
        deploy(client, endpoint_name, model_name, scoring_script)


if __name__ == "__main__":
    main()
