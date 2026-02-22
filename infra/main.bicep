// ─── Azure Container App Infrastructure ─────────────────────────────
// Deploys: Resource Group resources including ACR, Log Analytics,
//          Container Apps Environment, and the Container App itself.
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

@description('Database connection URL')
param databaseUrl string = 'sqlite:///data/vocabulary.db'

@secure()
@description('Azure OpenAI API key (optional)')
param azureOpenaiApiKey string = ''

@description('Azure OpenAI endpoint URL (optional)')
param azureOpenaiEndpoint string = ''

@description('Azure OpenAI deployment name (optional)')
param azureOpenaiDeployment string = ''

@description('Deploy the Container App (set false for infra-only bootstrap)')
param deployApp bool = true

// ─── Variables ──────────────────────────────────────────────────────

var uniqueSuffix = uniqueString(resourceGroup().id, appName)
var acrName = replace('acr${appName}${uniqueSuffix}', '-', '')
var logAnalyticsName = 'log-${appName}-${uniqueSuffix}'
var containerEnvName = 'cae-${appName}'
var containerAppName = 'ca-${appName}'
var storageName = replace('st${appName}${uniqueSuffix}', '-', '')

// ─── Azure Container Registry ───────────────────────────────────────

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
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

// ─── Azure Storage Account (for persistent SQLite data) ─────────────

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: substring(storageName, 0, min(length(storageName), 24))
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    minimumTlsVersion: 'TLS1_2'
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
  parent: fileService
  name: 'vocab-data'
  properties: {
    shareQuota: 1 // 1 GB — plenty for SQLite
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

// ─── Storage Mount in Environment ───────────────────────────────────

resource envStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: containerEnv
  name: 'vocabdata'
  properties: {
    azureFile: {
      accountName: storageAccount.name
      accountKey: storageAccount.listKeys().keys[0].value
      shareName: fileShare.name
      accessMode: 'ReadWrite'
    }
  }
}

// ─── Container App ──────────────────────────────────────────────────

resource containerApp 'Microsoft.App/containerApps@2024-03-01' = if (deployApp) {
  name: containerAppName
  location: location
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
            { name: 'DATABASE_URL', value: databaseUrl }
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
          volumeMounts: [
            {
              volumeName: 'vocab-data'
              mountPath: '/app/data'
            }
          ]
        }
      ]
      volumes: [
        {
          name: 'vocab-data'
          storageType: 'AzureFile'
          storageName: envStorage.name
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
output appUrl string = deployApp ? 'https://${containerApp.properties.configuration.ingress.fqdn}' : ''

@description('ACR login server')
output acrLoginServer string = acr.properties.loginServer

@description('ACR name')
output acrName string = acr.name

@description('Container App name')
output containerAppName string = deployApp ? containerApp.name : ''

@description('Resource group name')
output resourceGroupName string = resourceGroup().name
