// ─── Azure Container App Infrastructure ─────────────────────────────
// Deploys: ACR, Log Analytics, PostgreSQL Flexible Server,
//          Container Apps Environment, and the Container App.
//
// Usage:
//   az deployment group create \
//     --resource-group <rg-name> \
//     --template-file infra/main.bicep \
//     --parameters infra/main.parameters.json

targetScope = 'resourceGroup'

// ─── Parameters ─────────────────────────────────────────────────────

@description('Base name for all resources (e.g., "vocab")')
@minLength(3)
param appName string = 'kids-vocab'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Container image tag (e.g., "latest", "v1.0.0", commit SHA)')
param imageTag string = 'latest'

@description('Number of CPU cores for the container (0.25, 0.5, 1.0, 2.0)')
@allowed(['0.25', '0.5', '1.0', '2.0'])
param cpuCores string = '0.5'

@description('Memory size in Gi (0.5, 1.0, 2.0, 4.0)')
@allowed(['0.5Gi', '1.0Gi', '2.0Gi', '4.0Gi'])
param memorySize string = '1.0Gi'

@description('Minimum number of replicas')
@minValue(0)
@maxValue(10)
param minReplicas int = 0

@description('Maximum number of replicas')
@minValue(1)
@maxValue(10)
param maxReplicas int = 2

@secure()
@description('Application secret key for session management')
param secretKey string

@secure()
@description('Azure OpenAI API key (optional)')
param azureOpenaiApiKey string = ''

@description('Azure OpenAI endpoint URL (optional)')
param azureOpenaiEndpoint string = ''

@description('Azure OpenAI deployment name (optional)')
param azureOpenaiDeployment string = ''

@description('Deploy the Container App (set false for infra-only bootstrap)')
param deployApp bool = true

// ─── PostgreSQL Parameters ──────────────────────────────────────────

@description('PostgreSQL administrator username')
param pgAdminUser string = 'vocab_admin'

@secure()
@description('PostgreSQL administrator password (min 8 chars, must include uppercase, lowercase, number)')
param pgAdminPassword string

@description('PostgreSQL database name')
param pgDatabaseName string = 'vocabulary'

@description('PostgreSQL SKU tier')
@allowed(['Burstable', 'GeneralPurpose', 'MemoryOptimized'])
param pgSkuTier string = 'Burstable'

@description('PostgreSQL SKU name (e.g., Standard_B1ms, Standard_D2s_v3)')
param pgSkuName string = 'Standard_B1ms'

@description('PostgreSQL storage size in GB')
@minValue(32)
@maxValue(16384)
param pgStorageSizeGB int = 32

@description('PostgreSQL major version')
@allowed(['14', '15', '16', '17'])
param pgVersion string = '16'

@description('PostgreSQL backup retention days')
@minValue(7)
@maxValue(35)
param pgBackupRetentionDays int = 7

// ─── Variables ──────────────────────────────────────────────────────

var uniqueSuffix = uniqueString(resourceGroup().id, appName)
var acrName = replace('acr${appName}${uniqueSuffix}', '-', '')
var logAnalyticsName = 'log-${appName}-${uniqueSuffix}'
var containerEnvName = 'cae-${appName}'
var containerAppName = 'ca-${appName}'
var pgServerName = 'pg-${appName}-${uniqueSuffix}'
var databaseUrl = 'postgresql://${pgAdminUser}:${pgAdminPassword}@${pgServer.properties.fullyQualifiedDomainName}:5432/${pgDatabaseName}?sslmode=require'

// ─── Azure Container Registry ───────────────────────────────────────

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  #disable-next-line BCP334
  name: substring(acrName, 0, min(length(acrName), 50))
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// ─── Log Analytics Workspace ────────────────────────────────────────

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// ─── Azure Database for PostgreSQL Flexible Server ──────────────────

resource pgServer 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' = {
  name: pgServerName
  location: location
  sku: {
    name: pgSkuName
    tier: pgSkuTier
  }
  properties: {
    version: pgVersion
    administratorLogin: pgAdminUser
    administratorLoginPassword: pgAdminPassword
    storage: {
      storageSizeGB: pgStorageSizeGB
    }
    backup: {
      backupRetentionDays: pgBackupRetentionDays
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// Allow Azure services (Container Apps) to connect to PostgreSQL
resource pgFirewallAllowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2022-12-01' = {
  parent: pgServer
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// Create the application database
resource pgDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2022-12-01' = {
  parent: pgServer
  name: pgDatabaseName
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ─── Container Apps Environment ─────────────────────────────────────

resource containerEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: containerEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// ─── Container App ──────────────────────────────────────────────────

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = if (deployApp) {
  name: containerAppName
  location: location
  dependsOn: [
    pgFirewallAllowAzure
    pgDatabase
  ]
  properties: {
    managedEnvironmentId: containerEnv.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 5001
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'secret-key'
          value: secretKey
        }
        {
          name: 'database-url'
          value: databaseUrl
        }
        {
          name: 'azure-openai-api-key'
          value: !empty(azureOpenaiApiKey) ? azureOpenaiApiKey : 'not-configured'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'vocab-app'
          image: '${acr.properties.loginServer}/${appName}:${imageTag}'
          resources: {
            cpu: json(cpuCores)
            memory: memorySize
          }
          env: [
            { name: 'APP_ENV', value: 'production' }
            { name: 'SECRET_KEY', secretRef: 'secret-key' }
            { name: 'DATABASE_URL', secretRef: 'database-url' }
            { name: 'HOST', value: '0.0.0.0' }
            { name: 'PORT', value: '5001' }
            { name: 'WORKERS', value: '2' }
            { name: 'AZURE_OPENAI_API_KEY', secretRef: 'azure-openai-api-key' }
            { name: 'AZURE_OPENAI_ENDPOINT', value: azureOpenaiEndpoint }
            { name: 'AZURE_OPENAI_DEPLOYMENT', value: azureOpenaiDeployment }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 5001
              }
              periodSeconds: 30
              failureThreshold: 3
              initialDelaySeconds: 10
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 5001
              }
              periodSeconds: 10
              failureThreshold: 3
              initialDelaySeconds: 5
            }
          ]
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
}

// ─── Outputs ────────────────────────────────────────────────────────

@description('The FQDN of the deployed Container App')
#disable-next-line BCP318
output appUrl string = deployApp ? 'https://${containerApp.properties.configuration.ingress.fqdn}' : ''

@description('ACR login server')
output acrLoginServer string = acr.properties.loginServer

@description('ACR name')
output acrName string = acr.name

@description('Container App name')
#disable-next-line BCP318
output containerAppName string = deployApp ? containerApp.name : ''

@description('Resource group name')
output resourceGroupName string = resourceGroup().name

@description('PostgreSQL server FQDN')
output pgServerFqdn string = pgServer.properties.fullyQualifiedDomainName

@description('PostgreSQL database name')
output pgDatabaseName string = pgDatabaseName
