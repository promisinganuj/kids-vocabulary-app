# Azure OpenAI Setup Guide

This guide will help you configure Azure OpenAI for the vocabulary app's word search functionality.

## Prerequisites

1. **Azure Subscription**: You need an active Azure subscription
2. **Azure OpenAI Resource**: You must have created an Azure OpenAI resource in the Azure portal
3. **Model Deployment**: You must have deployed a chat model (like GPT-3.5-turbo or GPT-4) in your Azure OpenAI resource

## Required Information

You'll need to gather the following information from your Azure OpenAI resource:

### 1. API Key
- Go to your Azure OpenAI resource in the Azure portal
- Navigate to "Keys and Endpoint" section
- Copy either KEY 1 or KEY 2

### 2. Endpoint
- In the same "Keys and Endpoint" section
- Copy the "Endpoint" URL (e.g., `https://your-resource-name.openai.azure.com/`)

### 3. Deployment Name
- Go to "Model deployments" in your Azure OpenAI resource
- Note the deployment name you created for your chat model (e.g., `gpt-35-turbo`)

### 4. API Version
- Use a recent API version like `2024-02-15-preview`
- Check Azure OpenAI documentation for the latest available versions

## Configuration

1. **Edit the .env file** in the `/app` directory:

```bash
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_actual_api_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=your_deployment_name_here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

2. **Replace the placeholder values** with your actual Azure OpenAI details:
   - `your_actual_api_key_here` → Your Azure OpenAI API key
   - `https://your-resource-name.openai.azure.com/` → Your Azure OpenAI endpoint
   - `your_deployment_name_here` → Your model deployment name

## Example Configuration

```bash
# Example (replace with your actual values)
AZURE_OPENAI_API_KEY=1234567890abcdef1234567890abcdef
AZURE_OPENAI_ENDPOINT=https://my-openai-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-35-turbo
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

## Testing

After configuration:

1. Restart the Flask application
2. Go to the management page: `http://localhost:5001/manage`
3. Try searching for a word to test the Azure OpenAI integration

## Troubleshooting

### Common Issues:

1. **"API key not configured" error**
   - Verify your `AZURE_OPENAI_API_KEY` is set correctly in `.env`
   - Make sure there are no extra spaces or quotes

2. **"Endpoint not configured" error**
   - Verify your `AZURE_OPENAI_ENDPOINT` is set correctly
   - Ensure the URL includes `https://` and ends with `/`

3. **"Deployment not configured" error**
   - Verify your `AZURE_OPENAI_DEPLOYMENT` matches exactly with your Azure deployment name
   - Check in Azure portal under "Model deployments"

4. **401 Unauthorized error**
   - Check if your API key is correct
   - Verify the key hasn't expired

5. **404 Not Found error**
   - Verify the endpoint URL is correct
   - Check if the deployment name is correct

6. **Rate limit errors**
   - Azure OpenAI has rate limits based on your pricing tier
   - Wait a moment and try again

## Security Notes

- Never commit your actual API keys to version control
- Keep your `.env` file secure and private
- Regularly rotate your API keys for security

## API Reference

The app uses the Azure OpenAI Chat Completions API:
- Endpoint: `{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api-version}`
- Method: POST
- Headers: `api-key: {your-api-key}`

For more information, see the [Azure OpenAI REST API documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/reference).
