# Azure Web App Deployment Guide - Backend Only

## Overview
This guide is for deploying only the **backend folder** to Azure Web App, with all configuration managed through Azure Web App application settings (no .env file needed).

## Prerequisites
1. Azure CLI installed and configured (`az login`)
2. Azure Web App already created
3. API keys ready (Gemini, Azure Search, etc.)

## File Structure (Backend Only)
```
backend/ (This becomes your project root)
├── startup.sh              # Azure startup script
├── gunicorn.conf.py         # Gunicorn configuration
├── requirements.txt         # Python dependencies
├── main.py                  # FastAPI application
├── config.py               # Settings (reads from Azure env vars)
├── prompts.py              # Application prompts
├── graph/                  # LangGraph components
├── providers/              # External service providers
└── tools/                  # Application tools
```

## Deployment Steps

### 1. Deploy Backend Code
Navigate to the backend folder and deploy:

```bash
# Navigate to backend folder
cd c:\Users\estef\Downloads\Prueba2\backend

# Deploy using Azure CLI (this uploads the backend folder as the root)
az webapp up --name <your-webapp-name> --resource-group <your-resource-group> --runtime PYTHON:3.11

# Set the startup command
az webapp config set --resource-group <your-resource-group> --name <your-webapp-name> --startup-file "startup.sh"
```

### 2. Configure Azure Web App Application Settings

Instead of using a .env file, configure all environment variables in Azure Web App settings:

```bash
# Basic Application Settings
az webapp config appsettings set --resource-group <your-resource-group> --name <your-webapp-name> --settings \
  APP_NAME="Legal Bot" \
  ENV="production" \
  PORT="8000" \
  CORS_ALLOW_ORIGINS="https://<your-webapp-name>.azurewebsites.net"

# Gemini API Configuration
az webapp config appsettings set --resource-group <your-resource-group> --name <your-webapp-name> --settings \
  GEMINI_API_KEY="<your-gemini-api-key>" \
  GEMINI_CHAT_MODEL="gemini-2.0-flash" \
  GEMINI_EMBED_MODEL="text-embedding-004" \
  EMBED_DIM="768"

# Azure Search Configuration (if using search)
az webapp config appsettings set --resource-group <your-resource-group> --name <your-webapp-name> --settings \
  AZURE_SEARCH_ENDPOINT="https://<your-search-service>.search.windows.net" \
  AZURE_SEARCH_INDEX="<your-index-name>" \
  AZURE_SEARCH_API_KEY="<your-search-api-key>" \
  AZURE_SEARCH_USE_MSI="false"

# Optional: Azure Blob Storage (if needed)
az webapp config appsettings set --resource-group <your-resource-group> --name <your-webapp-name> --settings \
  AZURE_BLOB_ACCOUNT_NAME="<your-storage-account>" \
  AZURE_BLOB_ACCOUNT_KEY="<your-storage-key>" \
  AZURE_BLOB_CONTAINER_NAME="<your-container>"

# Additional Settings
az webapp config appsettings set --resource-group <your-resource-group> --name <your-webapp-name> --settings \
  USE_SEMANTIC_RANKER="false" \
  SEMANTIC_CONFIG_NAME="legal-semantic" \
  SEMANTIC_LANGUAGE="es-es"
```

### 3. Enable Logging
```bash
az webapp log config --name <your-webapp-name> --resource-group <your-resource-group> --web-server-logging filesystem
```

### 4. Verify Deployment
```bash
# Health check
curl https://<your-webapp-name>.azurewebsites.net/healthz

# Expected response: {"status": "ok", "env": "production"}
```

## Alternative: Azure Portal Configuration

### 1. Deploy Code via ZIP
1. Navigate to backend folder
2. Create a ZIP file of all contents
3. Go to Azure Portal → Your Web App → Deployment Center
4. Upload ZIP file

### 2. Configure Settings via Portal
1. Go to Azure Portal → Your Web App → Configuration
2. Add the following Application Settings:

| Name | Value |
|------|-------|
| APP_NAME | Legal Bot |
| ENV | production |
| PORT | 8000 |
| CORS_ALLOW_ORIGINS | https://your-webapp-name.azurewebsites.net |
| GEMINI_API_KEY | your-gemini-api-key |
| GEMINI_CHAT_MODEL | gemini-2.0-flash |
| GEMINI_EMBED_MODEL | text-embedding-004 |
| EMBED_DIM | 768 |
| AZURE_SEARCH_ENDPOINT | https://your-search-service.search.windows.net |
| AZURE_SEARCH_INDEX | your-index-name |
| AZURE_SEARCH_API_KEY | your-search-api-key |
| AZURE_SEARCH_USE_MSI | false |

### 3. Set Startup Command
1. Go to Configuration → General Settings
2. Set Startup Command to: `startup.sh`
3. Save changes

## PowerShell Deployment Script (Backend Only)

```powershell
param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,
    
    [Parameter(Mandatory=$true)]
    [string]$WebAppName,
    
    [Parameter(Mandatory=$true)]
    [string]$GeminiApiKey,
    
    [Parameter(Mandatory=$false)]
    [string]$AzureSearchEndpoint = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AzureSearchIndex = "",
    
    [Parameter(Mandatory=$false)]
    [string]$AzureSearchApiKey = ""
)

# Navigate to backend folder
Set-Location "c:\Users\estef\Downloads\Prueba2\backend"

Write-Host "Deploying backend to Azure Web App: $WebAppName" -ForegroundColor Green

# Deploy code
az webapp up --name $WebAppName --resource-group $ResourceGroup --runtime PYTHON:3.11

# Set startup command
az webapp config set --resource-group $ResourceGroup --name $WebAppName --startup-file "startup.sh"

# Configure application settings
az webapp config appsettings set --resource-group $ResourceGroup --name $WebAppName --settings `
  APP_NAME="Legal Bot" `
  ENV="production" `
  PORT="8000" `
  CORS_ALLOW_ORIGINS="https://$WebAppName.azurewebsites.net" `
  GEMINI_API_KEY="$GeminiApiKey" `
  GEMINI_CHAT_MODEL="gemini-2.0-flash" `
  GEMINI_EMBED_MODEL="text-embedding-004" `
  EMBED_DIM="768"

if ($AzureSearchEndpoint -and $AzureSearchIndex) {
    az webapp config appsettings set --resource-group $ResourceGroup --name $WebAppName --settings `
      AZURE_SEARCH_ENDPOINT="$AzureSearchEndpoint" `
      AZURE_SEARCH_INDEX="$AzureSearchIndex" `
      AZURE_SEARCH_API_KEY="$AzureSearchApiKey" `
      AZURE_SEARCH_USE_MSI="false"
}

# Enable logging
az webapp log config --name $WebAppName --resource-group $ResourceGroup --web-server-logging filesystem

Write-Host "Deployment completed! App available at: https://$WebAppName.azurewebsites.net" -ForegroundColor Green
```

## Key Benefits of Backend-Only Deployment

1. **Cleaner separation**: Backend and indexing are separate projects
2. **Smaller deployment**: Only bot code, faster deployments
3. **Azure-native configuration**: All settings managed in Azure Portal
4. **No .env file**: More secure, follows Azure best practices
5. **Easier management**: Settings can be updated without redeployment

## Monitoring and Troubleshooting

```bash
# View logs
az webapp log tail --name <your-webapp-name> --resource-group <your-resource-group>

# Check application settings
az webapp config appsettings list --name <your-webapp-name> --resource-group <your-resource-group>

# Restart app if needed
az webapp restart --name <your-webapp-name> --resource-group <your-resource-group>
```

## Testing Your API

```bash
# Health check
curl https://<your-webapp-name>.azurewebsites.net/healthz

# Chat endpoint test
curl -X POST https://<your-webapp-name>.azurewebsites.net/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test message",
    "top_k": 6
  }'
```

This approach gives you a clean, production-ready deployment focused only on your bot functionality! 🚀
