# Azure Container App Deployment

This directory contains infrastructure-as-code (Bicep) and deployment scripts to host the Kids Vocabulary App on **Azure Container Apps**.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Azure Resource Group (rg-kids-vocab)                        │
│                                                              │
│  ┌────────────────┐    ┌──────────────────────────────────┐  │
│  │ Azure Container│    │  Container Apps Environment       │  │
│  │ Registry (ACR) │───▶│  ┌────────────────────────────┐  │  │
│  │                │    │  │ Container App (vocab-app)   │  │  │
│  └────────────────┘    │  │  - FastAPI + Gunicorn       │  │  │
│                        │  │  - Port 5001                │  │  │
│  ┌────────────────┐    │  │  - Auto-scaling 0-2         │  │  │
│  │ Log Analytics  │◀───│  └─────────┬──────────────────┘  │  │
│  │ Workspace      │    │            │                      │  │
│  └────────────────┘    └────────────┼──────────────────────┘  │
│                                     │                         │
│  ┌────────────────┐                 │                         │
│  │ Azure Storage  │◀────────────────┘                         │
│  │ (File Share)   │  /app/data mount (SQLite persistence)     │
│  └────────────────┘                                           │
└──────────────────────────────────────────────────────────────┘
```

## What Gets Deployed

| Resource | Purpose |
|----------|---------|
| **Azure Container Registry** | Stores Docker images (Basic tier) |
| **Container Apps Environment** | Managed Kubernetes-based hosting |
| **Container App** | The vocabulary app (auto-scales 0–2 replicas) |
| **Azure Storage (File Share)** | Persistent volume for SQLite database |
| **Log Analytics Workspace** | Centralized logging and monitoring |

## Quick Start — Manual Deployment

### Prerequisites

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed
- [Docker](https://docs.docker.com/get-docker/) installed
- An Azure subscription

### Steps

```bash
# 1. Login to Azure
az login

# 2. (Optional) Set your secret key — one is auto-generated if omitted
export SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# 3. Deploy everything
./infra/deploy.sh

# 4. (Subsequent deploys) Update just the app image
./infra/deploy.sh --update-only
```

### Configuration

Override defaults via environment variables:

```bash
export RESOURCE_GROUP=rg-kids-vocab      # Azure resource group name
export LOCATION=australiaeast            # Azure region
export APP_NAME=kids-vocab               # Base name for resources
export IMAGE_TAG=v1.0.0                  # Image tag (default: latest)
export SECRET_KEY=your-secret-key        # App secret (auto-generated if empty)
export DATABASE_URL=sqlite:///data/vocabulary.db

# Optional: Azure OpenAI
export AZURE_OPENAI_API_KEY=your-key
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_DEPLOYMENT=your-deployment

./infra/deploy.sh
```

## Quick Start — GitHub Actions (CI/CD)

Automated deployment on every push to `main`.

### 1. Create an Azure Service Principal

```bash
az ad sp create-for-rbac \
  --name "sp-kids-vocab-deploy" \
  --role contributor \
  --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID> \
  --sdk-auth
```

Copy the entire JSON output.

### 2. Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** in your GitHub repo:

| Secret | Required | Description |
|--------|----------|-------------|
| `AZURE_CREDENTIALS` | Yes | The full JSON from `az ad sp create-for-rbac --sdk-auth` |
| `SECRET_KEY` | Yes | App session secret key |
| `AZURE_OPENAI_API_KEY` | No | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | No | Azure OpenAI endpoint |
| `AZURE_OPENAI_DEPLOYMENT` | No | Azure OpenAI deployment name |

### 3. Configure GitHub Variables

Go to **Settings → Secrets and variables → Actions → Variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `RESOURCE_GROUP` | `rg-kids-vocab` | Azure resource group name |
| `LOCATION` | `australiaeast` | Azure region |

### 4. Create a GitHub Environment

Go to **Settings → Environments** and create a `production` environment. Optionally add:
- Required reviewers (for manual approval before deploy)
- Wait timer

### 5. Deploy

Push to `main` or manually trigger from **Actions → Deploy to Azure Container Apps → Run workflow**.

## Post-Deployment

### View logs

```bash
az containerapp logs show \
  --name ca-kids-vocab \
  --resource-group rg-kids-vocab \
  --follow
```

### Check app status

```bash
az containerapp show \
  --name ca-kids-vocab \
  --resource-group rg-kids-vocab \
  --query "{status:properties.runningStatus, fqdn:properties.configuration.ingress.fqdn, replicas:properties.template.scale}"
```

### Scale manually

```bash
az containerapp update \
  --name ca-kids-vocab \
  --resource-group rg-kids-vocab \
  --min-replicas 1 \
  --max-replicas 5
```

### Tear down everything

```bash
az group delete --name rg-kids-vocab --yes --no-wait
```

## Cost Estimate

With the default configuration (scale-to-zero, Basic ACR, minimal storage):

| Resource | Estimated Monthly Cost |
|----------|----------------------|
| Container Apps (0-2 replicas, scale-to-zero) | ~$0 idle, ~$5-15 active |
| Container Registry (Basic) | ~$5 |
| Storage Account (1 GB file share) | ~$0.05 |
| Log Analytics (first 5 GB free) | ~$0 |
| **Total (low traffic)** | **~$5-20/month** |

> Scale-to-zero means you pay nothing when no one is using the app. First request after idle has a ~10-15s cold start.
