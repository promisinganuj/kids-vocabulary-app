#!/bin/bash

echo "🐳 VCE Vocabulary Flashcards - Azure Container Instance Deployment"
echo "=================================================================="

# Configuration
RESOURCE_GROUP="vocabulary-flashcards-container-rg"
CONTAINER_NAME="vocabulary-flashcards"
LOCATION="eastus"
IMAGE_NAME="vocabulary-flashcards:latest"
DNS_NAME_LABEL=""

# Prompt for DNS name
read -p "Enter a unique DNS name (e.g., my-vocab-app-123): " DNS_NAME_LABEL

if [ -z "$DNS_NAME_LABEL" ]; then
    echo "❌ DNS name cannot be empty!"
    exit 1
fi

echo "📋 Container Deployment Configuration:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   Container Name: $CONTAINER_NAME"
echo "   DNS Name: $DNS_NAME_LABEL"
echo "   Location: $LOCATION"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "💡 Install it from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Build Docker image
echo "🏗️  Building Docker image..."
docker build -t $IMAGE_NAME .

# Login to Azure
echo "🔐 Checking Azure login..."
if ! az account show &> /dev/null; then
    echo "🔑 Please login to Azure..."
    az login
fi

# Create resource group
echo "🏗️  Creating resource group..."
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION

# Create Azure Container Registry (optional, for image hosting)
ACR_NAME="${DNS_NAME_LABEL//-/}acr"
echo "📦 Creating Azure Container Registry..."
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $ACR_NAME \
    --sku Basic \
    --admin-enabled true

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query "loginServer" --output tsv)

# Tag and push image to ACR
echo "📤 Pushing image to Azure Container Registry..."
docker tag $IMAGE_NAME $ACR_LOGIN_SERVER/$IMAGE_NAME
az acr build --registry $ACR_NAME --image $IMAGE_NAME .

# Create container instance
echo "🚀 Creating Azure Container Instance..."
az container create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --image $ACR_LOGIN_SERVER/$IMAGE_NAME \
    --registry-login-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_NAME \
    --registry-password $(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv) \
    --dns-name-label $DNS_NAME_LABEL \
    --ports 8000 \
    --cpu 1 \
    --memory 1 \
    --environment-variables FLASK_ENV=production \
    --restart-policy Always

echo "✅ Container deployment completed!"
echo ""
echo "🎉 Your application is available at:"
echo "   🌐 http://$DNS_NAME_LABEL.$LOCATION.azurecontainer.io:8000"
echo ""
echo "💡 Useful commands:"
echo "   - View logs: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
echo "   - Restart: az container restart --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME"
echo "   - Delete: az group delete --name $RESOURCE_GROUP"
echo ""
echo "💰 Estimated cost: ~$0.40/day (pay-per-second billing)"
