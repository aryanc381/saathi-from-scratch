// Sets the app settings of both sites. Runs after the API's Key Vault role is granted so secret references resolve.
param apiName string
param webName string
param apiSettings object
param webSettings object

resource api 'Microsoft.Web/sites@2023-12-01' existing = {
  name: apiName
}

resource web 'Microsoft.Web/sites@2023-12-01' existing = {
  name: webName
}

resource apiConfig 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: api
  name: 'appsettings'
  properties: apiSettings
}

resource webConfig 'Microsoft.Web/sites/config@2023-12-01' = {
  parent: web
  name: 'appsettings'
  properties: webSettings
}
