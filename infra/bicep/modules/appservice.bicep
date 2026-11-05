// Responsible for hosting: one Linux App Service plan hosting the Python API and the .NET UI. Code is zip-deployed, so no containers are involved.
param planName string
param apiName string
param webName string
param location string

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  kind: 'linux'
  sku: { name: 'B1', tier: 'Basic' }
  properties: { reserved: true }
}

resource api 'Microsoft.Web/sites@2023-12-01' = {
  name: apiName
  location: location
  kind: 'app,linux'
  identity: { type: 'SystemAssigned' }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.12'
      appCommandLine: 'bash startup.sh'
      alwaysOn: true
    }
  }
}

resource web 'Microsoft.Web/sites@2023-12-01' = {
  name: webName
  location: location
  kind: 'app,linux'
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'DOTNETCORE|10.0'
      alwaysOn: true
      webSocketsEnabled: true
    }
  }
}

output apiPrincipalId string = api.identity.principalId
