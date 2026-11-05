// Responsible for the Key Vault (RBAC mode) that holds every runtime secret; the API reads them through App Service Key Vault references.
param name string
param location string
@secure()
param secrets object

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
  }
}

resource secret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = [for item in items(secrets): {
  parent: vault
  name: item.key
  properties: { value: item.value }
}]
