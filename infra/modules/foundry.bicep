// Responsible for the Azure AI Foundry (AI Services) account with the GPT chat and embedding model deployments.
param name string
param location string
param chatDeploymentName string
param chatModelName string
param chatModelVersion string
param chatCapacity int
param embedDeploymentName string
param embedModelName string
param embedModelVersion string
param embedCapacity int

resource account 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
  }
}

resource chat 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: account
  name: chatDeploymentName
  sku: { name: 'GlobalStandard', capacity: chatCapacity }
  properties: {
    model: { format: 'OpenAI', name: chatModelName, version: chatModelVersion }
  }
}

// Deployments on one account are created one at a time, so embed waits for chat.
resource embed 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: account
  name: embedDeploymentName
  sku: { name: 'Standard', capacity: embedCapacity }
  properties: {
    model: { format: 'OpenAI', name: embedModelName, version: embedModelVersion }
  }
  dependsOn: [chat]
}
