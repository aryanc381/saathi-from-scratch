// Azure ML workspace with its own Key Vault. Online endpoints for intent and radar are created later by ml/azureml.
param name string
param keyVaultName string
param location string
param storageId string
param insightsId string

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A', name: 'standard' }
    accessPolicies: []
    enableRbacAuthorization: false
  }
}

resource workspace 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: name
  location: location
  sku: { name: 'Basic', tier: 'Basic' }
  identity: { type: 'SystemAssigned' }
  properties: {
    friendlyName: name
    storageAccount: storageId
    keyVault: vault.id
    applicationInsights: insightsId
  }
}
