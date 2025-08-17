#!/bin/bash

echo "🚀 VCE Vocabulary Flashcards - Azure Deployment Script"
echo "======================================================="

# Configuration
RESOURCE_GROUP="vocabulary-flashcards-rg"
APP_SERVICE_PLAN="vocabulary-flashcards-plan"
LOCATION="eastus"
RUNTIME="PYTHON|3.11"

# Prompt for app name
read -p "Enter a unique app name (e.g., my-vocab-flashcards-123): " APP_NAME

if [ -z "$APP_NAME" ]; then
    echo "❌ App name cannot be empty!"
    exit 1
fi

echo "📋 Deployment Configuration:"
echo "   Resource Group: $RESOURCE_GROUP"
echo "   App Name: $APP_NAME"
echo "   Location: $LOCATION"
echo "   Runtime: $RUNTIME"
echo ""

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed!"
    echo "💡 Install it from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Login check
echo "🔐 Checking Azure login status..."
if ! az account show &> /dev/null; then
    echo "🔑 Please login to Azure..."
    az login
fi

# Get subscription info
SUBSCRIPTION=$(az account show --query "name" -o tsv)
echo "✅ Logged in to subscription: $SUBSCRIPTION"

# Create resource group
echo "🏗️  Creating resource group..."
az group create \
    --name $RESOURCE_GROUP \
    --location $LOCATION \
    --output table

# Create App Service plan (Free tier)
echo "📊 Creating App Service plan..."
az appservice plan create \
    --name $APP_SERVICE_PLAN \
    --resource-group $RESOURCE_GROUP \
    --sku FREE \
    --is-linux \
    --output table

# Create web app
echo "🌐 Creating web app..."
az webapp create \
    --resource-group $RESOURCE_GROUP \
    --plan $APP_SERVICE_PLAN \
    --name $APP_NAME \
    --runtime "$RUNTIME" \
    --output table

# Configure app settings
echo "⚙️  Configuring app settings..."
az webapp config appsettings set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --settings \
        FLASK_ENV=production \
        PYTHONPATH=/home/site/wwwroot \
        --output table

# Set startup command
echo "🚀 Setting startup command..."
az webapp config set \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --startup-file "startup.sh" \
    --output table

# Configure deployment source
echo "📂 Configuring Git deployment..."
DEPLOYMENT_URL=$(az webapp deployment source config-local-git \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query url -o tsv)

echo "✅ Deployment configured!"
echo ""
echo "🎉 Next Steps:"
echo "1. Add Azure remote to your git repository:"
echo "   git remote add azure $DEPLOYMENT_URL"
echo ""
echo "2. Deploy your application:"
echo "   git add ."
echo "   git commit -m 'Deploy to Azure'"
echo "   git push azure main"
echo ""
echo "3. Your app will be available at:"
echo "   🌐 https://$APP_NAME.azurewebsites.net"
echo ""
echo "4. Monitor deployment logs:"
echo "   az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo "💡 Useful commands:"
echo "   - View app logs: az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP"
echo "   - Restart app: az webapp restart --name $APP_NAME --resource-group $RESOURCE_GROUP"
echo "   - Delete resources: az group delete --name $RESOURCE_GROUP"
echo ""
echo "🎊 Happy studying with your cloud-hosted vocabulary app!"
