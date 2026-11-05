// Azure SQL server and Basic database. Add your own IP as a firewall rule to run data/seed/load_sql.py from a laptop.
param serverName string
param databaseName string
param location string
param adminLogin string
@secure()
param adminPassword string

resource server 'Microsoft.Sql/servers@2023-08-01-preview' = {
  name: serverName
  location: location
  properties: {
    administratorLogin: adminLogin
    administratorLoginPassword: adminPassword
    minimalTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource database 'Microsoft.Sql/servers/databases@2023-08-01-preview' = {
  parent: server
  name: databaseName
  location: location
  sku: { name: 'Basic', tier: 'Basic' }
}

// 0.0.0.0 is Azure's marker for "allow Azure services", which lets the App Service reach the database.
resource allowAzure 'Microsoft.Sql/servers/firewallRules@2023-08-01-preview' = {
  parent: server
  name: 'AllowAzureServices'
  properties: { startIpAddress: '0.0.0.0', endIpAddress: '0.0.0.0' }
}
