#!/bin/bash
# Responsible for deleting everything in a Saathi resource group after the demo, so nothing keeps costing money.
# It also purges the soft-deleted Key Vaults and Foundry accounts, so the same names can be deployed again.
# Usage: scripts/teardown.sh <resource-group>
set -euo pipefail

group=$1

read -r -p "This deletes everything in '$group'. Type the group name to confirm: " answer
if [ "$answer" != "$group" ]; then
  echo "Cancelled."
  exit 1
fi

# These names and the location must be read before the group is deleted.
vaults=$(az keyvault list --resource-group "$group" --query "[].name" --output tsv)
accounts=$(az cognitiveservices account list --resource-group "$group" --query "[].name" --output tsv)
location=$(az group show --name "$group" --query location --output tsv)

az group delete --name "$group" --yes

for vault in $vaults; do
  az keyvault purge --name "$vault"
done
for account in $accounts; do
  az cognitiveservices account purge --name "$account" --resource-group "$group" --location "$location"
done

echo "Everything in '$group' is deleted."
