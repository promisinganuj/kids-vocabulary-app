#!/usr/bin/env bash
# ─── Deploy Kids Vocabulary App to Azure Container Apps ──────────────
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - Docker installed (for building the image)
#
# Usage:
#   ./infra/deploy.sh                    # First-time deployment
#   ./infra/deploy.sh --update-only      # Update app image only (skip infra)
#
# Environment variables (override defaults):
#   RESOURCE_GROUP   — Azure resource group name  (default: rg-kids-vocab)
#   LOCATION         — Azure region               (default: australiaeast)
#   APP_NAME         — Base name for resources     (default: kids-vocab)
#   IMAGE_TAG        — Container image tag         (default: latest)
#   SECRET_KEY       — App secret key              (auto-generated if empty)
#   DATABASE_URL     — Database connection string  (default: sqlite:///data/vocabulary.db)
# ─────────────────────────────────────────────────────────────────────

set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────

RESOURCE_GROUP="${RESOURCE_GROUP:-rg-kids-vocab}"
LOCATION="${LOCATION:-australiaeast}"
APP_NAME="${APP_NAME:-kids-vocab}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DATABASE_URL="${DATABASE_URL:-sqlite:///data/vocabulary.db}"
UPDATE_ONLY=false

# Parse arguments
for arg in "$@"; do
    case $arg in
        --update-only) UPDATE_ONLY=true ;;
        --help|-h)
            echo "Usage: $0 [--update-only]"
            echo ""
            echo "Options:"
            echo "  --update-only   Skip infrastructure deployment, only rebuild and push image"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Environment variables:"
            echo "  RESOURCE_GROUP   Azure resource group name  (default: rg-kids-vocab)"
            echo "  LOCATION         Azure region               (default: australiaeast)"
            echo "  APP_NAME         Base name for resources     (default: kids-vocab)"
            echo "  IMAGE_TAG        Container image tag         (default: latest)"
            echo "  SECRET_KEY       App secret key              (auto-generated if empty)"
            echo "  DATABASE_URL     Database connection string  (default: sqlite:///data/vocabulary.db)"
            exit 0
            ;;
    esac
done

# Generate a secret key if not provided
if [[ -z "${SECRET_KEY:-}" ]]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    echo "Generated SECRET_KEY (save this for future deployments):"
    echo "  export SECRET_KEY=$SECRET_KEY"
    echo ""
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "═══════════════════════════════════════════════════════════════"
echo "  Deploying Kids Vocabulary App to Azure Container Apps"
echo "═══════════════════════════════════════════════════════════════"
echo "  Resource Group : $RESOURCE_GROUP"
echo "  Location       : $LOCATION"
echo "  App Name       : $APP_NAME"
echo "  Image Tag      : $IMAGE_TAG"
echo "  Update Only    : $UPDATE_ONLY"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# ─── Step 1: Create Resource Group ───────────────────────────────────

if [[ "$UPDATE_ONLY" == "false" ]]; then
    echo "▸ Creating resource group '$RESOURCE_GROUP' in '$LOCATION'..."
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --output none

    # ─── Step 2: Deploy Infrastructure (Bicep) ──────────────────────

    echo "▸ Deploying Azure infrastructure — phase 1: ACR & supporting resources..."
    INFRA_OUTPUT=$(az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$SCRIPT_DIR/main.bicep" \
        --parameters "$SCRIPT_DIR/main.parameters.json" \
        --parameters \
            secretKey="$SECRET_KEY" \
            imageTag="$IMAGE_TAG" \
            databaseUrl="$DATABASE_URL" \
            azureOpenaiApiKey="${AZURE_OPENAI_API_KEY:-}" \
            azureOpenaiEndpoint="${AZURE_OPENAI_ENDPOINT:-}" \
            azureOpenaiDeployment="${AZURE_OPENAI_DEPLOYMENT:-}" \
            deployApp=false \
        --query "properties.outputs" \
        --output json)

    ACR_NAME=$(echo "$INFRA_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['acrName']['value'])")
    ACR_LOGIN_SERVER=$(echo "$INFRA_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['acrLoginServer']['value'])")

    echo "  ACR: $ACR_LOGIN_SERVER"
    echo ""

    # ─── Step 3: Build & Push Docker Image ──────────────────────────

    echo "▸ Logging into Azure Container Registry..."
    az acr login --name "$ACR_NAME"

    echo "▸ Building Docker image..."
    docker build \
        -t "$ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG" \
        -t "$ACR_LOGIN_SERVER/$APP_NAME:$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
        -f "$PROJECT_ROOT/app/Dockerfile" \
        "$PROJECT_ROOT/app"

    echo "▸ Pushing image to ACR..."
    docker push "$ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG"
    docker push "$ACR_LOGIN_SERVER/$APP_NAME:$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'unknown')" 2>/dev/null || true

    # ─── Step 4: Deploy Container App (Bicep phase 2) ───────────────

    echo "▸ Deploying Azure infrastructure — phase 2: Container App..."
    DEPLOY_OUTPUT=$(az deployment group create \
        --resource-group "$RESOURCE_GROUP" \
        --template-file "$SCRIPT_DIR/main.bicep" \
        --parameters "$SCRIPT_DIR/main.parameters.json" \
        --parameters \
            secretKey="$SECRET_KEY" \
            imageTag="$IMAGE_TAG" \
            databaseUrl="$DATABASE_URL" \
            azureOpenaiApiKey="${AZURE_OPENAI_API_KEY:-}" \
            azureOpenaiEndpoint="${AZURE_OPENAI_ENDPOINT:-}" \
            azureOpenaiDeployment="${AZURE_OPENAI_DEPLOYMENT:-}" \
            deployApp=true \
        --query "properties.outputs" \
        --output json)

    ACR_NAME=$(echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['acrName']['value'])")
    ACR_LOGIN_SERVER=$(echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['acrLoginServer']['value'])")
    CONTAINER_APP_NAME=$(echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['containerAppName']['value'])")
    APP_URL=$(echo "$DEPLOY_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['appUrl']['value'])")
else
    # Fetch existing resource names for update-only mode
    echo "▸ Fetching existing infrastructure details..."
    ACR_NAME=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[0].name" --output tsv)
    ACR_LOGIN_SERVER=$(az acr list --resource-group "$RESOURCE_GROUP" --query "[0].loginServer" --output tsv)
    CONTAINER_APP_NAME=$(az containerapp list --resource-group "$RESOURCE_GROUP" --query "[0].name" --output tsv)

    echo "  ACR: $ACR_LOGIN_SERVER"
    echo ""

    # ─── Build & Push Docker Image ──────────────────────────────────

    echo "▸ Logging into Azure Container Registry..."
    az acr login --name "$ACR_NAME"

    echo "▸ Building Docker image..."
    docker build \
        -t "$ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG" \
        -t "$ACR_LOGIN_SERVER/$APP_NAME:$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'unknown')" \
        -f "$PROJECT_ROOT/app/Dockerfile" \
        "$PROJECT_ROOT/app"

    echo "▸ Pushing image to ACR..."
    docker push "$ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG"
    docker push "$ACR_LOGIN_SERVER/$APP_NAME:$(git -C "$PROJECT_ROOT" rev-parse --short HEAD 2>/dev/null || echo 'unknown')" 2>/dev/null || true

    # ─── Update Container App to use new image ──────────────────────

    echo "▸ Updating Container App with new image..."
    az containerapp update \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --image "$ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG" \
        --output none

    APP_URL="https://$(az containerapp show \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query 'properties.configuration.ingress.fqdn' \
        --output tsv)"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "  ✓ Deployment complete!"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  App URL     : $APP_URL"
echo "  ACR         : $ACR_LOGIN_SERVER"
echo "  App Name    : $CONTAINER_APP_NAME"
echo "  Image       : $ACR_LOGIN_SERVER/$APP_NAME:$IMAGE_TAG"
echo ""
echo "  View logs   : az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo "  View app    : az containerapp show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
