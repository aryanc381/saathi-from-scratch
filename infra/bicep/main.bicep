// Responsible for wiring all Azure modules together: names, secrets, access and app settings.
// It deploys every Azure resource Saathi needs into one resource group.
// Deploy: az deployment group create -g <rg> -f infra/bicep/main.bicep -p @infra/params/parameters.json sqlAdminPassword=... jwtSecret=...
targetScope = 'resourceGroup'

param namePrefix string
param location string
param sqlAdminLogin string
@secure()
param sqlAdminPassword string
@secure()
param jwtSecret string
param chatDeploymentName string
param chatModelName string
param chatModelVersion string
param chatCapacity int
param embedDeploymentName string
param embedModelName string
param embedModelVersion string
param embedCapacity int
param searchIndexName string

// Names are plain variables so existing-resource lookups below can be calculated at the start of the deployment.
var suffix = take(uniqueString(resourceGroup().id), 6)
var storageName = 'st${namePrefix}${suffix}'
var vaultName = 'kv-${namePrefix}-${suffix}'
var mlVaultName = 'kv-${namePrefix}-ml-${suffix}'
var foundryName = '${namePrefix}-ai-${suffix}'
var searchName = '${namePrefix}-search-${suffix}'
var sqlServerName = '${namePrefix}-sql-${suffix}'
var sqlDatabaseName = namePrefix
var mlName = '${namePrefix}-ml-${suffix}'
var planName = '${namePrefix}-plan'
var apiName = '${namePrefix}-api-${suffix}'
var webName = '${namePrefix}-web-${suffix}'

// Where the secrets live; App Service settings point at them with Key Vault references.
var vaultUri = 'https://${vaultName}${environment().suffixes.keyvaultDns}/'
// The connection string the API uses for SQL. It is stored in Key Vault, never in plain app settings.
var sqlConnectionString = 'Driver={ODBC Driver 18 for SQL Server};Server=tcp:${sqlServerName}${environment().suffixes.sqlServerHostname},1433;Database=${sqlDatabaseName};Uid=${sqlAdminLogin};Pwd=${sqlAdminPassword};Encrypt=yes;TrustServerCertificate=no;'
// Built-in Azure role id for 'Key Vault Secrets User'.
var keyVaultSecretsUserRole = '4633458b-17de-408a-b874-0521c86b0cc7'

// Each module below creates one Azure service.
module monitor 'modules/monitor.bicep' = {
  name: 'monitor'
  params: { name: namePrefix, location: location }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: { name: storageName, location: location }
}

module foundry 'modules/foundry.bicep' = {
  name: 'foundry'
  params: {
    name: foundryName
    location: location
    chatDeploymentName: chatDeploymentName
    chatModelName: chatModelName
    chatModelVersion: chatModelVersion
    chatCapacity: chatCapacity
    embedDeploymentName: embedDeploymentName
    embedModelName: embedModelName
    embedModelVersion: embedModelVersion
    embedCapacity: embedCapacity
  }
}

module search 'modules/search.bicep' = {
  name: 'search'
  params: { name: searchName, location: location }
}

module sql 'modules/sql.bicep' = {
  name: 'sql'
  params: {
    serverName: sqlServerName
    databaseName: sqlDatabaseName
    location: location
    adminLogin: sqlAdminLogin
    adminPassword: sqlAdminPassword
  }
}

module ml 'modules/ml.bicep' = {
  name: 'ml'
  params: {
    name: mlName
    keyVaultName: mlVaultName
    location: location
    storageId: storage.outputs.id
    insightsId: monitor.outputs.insightsId
  }
}

module apps 'modules/appservice.bicep' = {
  name: 'apps'
  params: { planName: planName, apiName: apiName, webName: webName, location: location }
}

resource foundryRef 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: foundryName
}

resource searchRef 'Microsoft.Search/searchServices@2023-11-01' existing = {
  name: searchName
}

resource storageRef 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageName
}

// Stores every secret in Key Vault. Keys are read straight from the resources, so none appear in this repo.
module keyvault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    name: vaultName
    location: location
    secrets: {
      'jwt-secret': jwtSecret
      'sql-connection-string': sqlConnectionString
      'openai-api-key': foundryRef.listKeys().key1
      'search-admin-key': searchRef.listAdminKeys().primaryKey
      'storage-connection-string': 'DefaultEndpointsProtocol=https;AccountName=${storageName};AccountKey=${storageRef.listKeys().keys[0].value};EndpointSuffix=${environment().suffixes.storage}'
    }
  }
  dependsOn: [foundry, search, storage]
}

resource vaultRef 'Microsoft.KeyVault/vaults@2023-07-01' existing = {
  name: vaultName
}

// Lets the API's managed identity read secrets; the web UI holds no secrets.
resource apiSecretsAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: vaultRef
  name: guid(vaultRef.id, 'api-kv-secrets-user')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRole)
    principalId: apps.outputs.apiPrincipalId
    principalType: 'ServicePrincipal'
  }
  dependsOn: [keyvault]
}

// Gives both sites their settings. Secrets are Key Vault references, not values.
module appSettings 'modules/appsettings.bicep' = {
  name: 'appsettings'
  params: {
    apiName: apiName
    webName: webName
    apiSettings: {
      LLM_PROVIDER: 'azure'
      RETRIEVER: 'azure'
      // Starts as 'local' because the Azure ML endpoints do not exist yet. After ml/azureml/scripts/deploy.py,
      // set ML_PROVIDER=azure and the four INTENT_/RADAR_ENDPOINT_ settings on the API app.
      ML_PROVIDER: 'local'
      SCM_DO_BUILD_DURING_DEPLOYMENT: 'true'
      AZURE_OPENAI_ENDPOINT: 'https://${foundryName}.openai.azure.com'
      AZURE_OPENAI_CHAT_DEPLOYMENT: chatDeploymentName
      AZURE_OPENAI_EMBED_DEPLOYMENT: embedDeploymentName
      AZURE_SEARCH_ENDPOINT: 'https://${searchName}.search.windows.net'
      AZURE_SEARCH_INDEX_NAME: searchIndexName
      JWT_SECRET: '@Microsoft.KeyVault(SecretUri=${vaultUri}secrets/jwt-secret/)'
      SQL_CONNECTION_STRING: '@Microsoft.KeyVault(SecretUri=${vaultUri}secrets/sql-connection-string/)'
      AZURE_OPENAI_API_KEY: '@Microsoft.KeyVault(SecretUri=${vaultUri}secrets/openai-api-key/)'
      AZURE_SEARCH_ADMIN_KEY: '@Microsoft.KeyVault(SecretUri=${vaultUri}secrets/search-admin-key/)'
    }
    webSettings: {
      API_URL: 'https://${apiName}.azurewebsites.net'
    }
  }
  dependsOn: [apiSecretsAccess]
}

output apiUrl string = 'https://${apiName}.azurewebsites.net'
output webUrl string = 'https://${webName}.azurewebsites.net'
output foundryEndpoint string = 'https://${foundryName}.openai.azure.com'
output searchEndpoint string = 'https://${searchName}.search.windows.net'
output sqlServer string = '${sqlServerName}${environment().suffixes.sqlServerHostname}'
output storageAccount string = storageName
output keyVault string = vaultName
output mlWorkspace string = mlName
