# 🎯 Backend-Only Azure Deployment Checklist

## ✅ Configuration Complete!

Your backend folder is now ready for Azure Web App deployment with all settings managed through Azure Application Settings (no .env file needed).

### 📁 **Deployment Structure**
```
backend/ (becomes your app root)
├── startup.sh          ✅ Azure startup script
├── gunicorn.conf.py     ✅ Optimized for Azure
├── requirements.txt     ✅ Updated (removed python-dotenv)
├── config.py           ✅ Reads from Azure env vars
├── main.py             ✅ FastAPI application
├── [other backend files]
```

### 🚀 **Quick Deployment Commands**

**Option 1: PowerShell Script (Recommended)**
```powershell
.\deploy-backend.ps1 -ResourceGroup "your-rg" -WebAppName "your-app" -GeminiApiKey "your-key"
```

**Option 2: Manual Azure CLI**
```bash
cd backend
az webapp up --name your-app --resource-group your-rg --runtime PYTHON:3.11
az webapp config set --resource-group your-rg --name your-app --startup-file "startup.sh"
# Then configure settings via Azure Portal or CLI
```

### ⚙️ **Required Azure Web App Settings**

These will be configured automatically by the script or manually via Azure Portal:

| Setting | Value | Required |
|---------|-------|----------|
| APP_NAME | Legal Bot | ✅ |
| ENV | production | ✅ |
| PORT | 8000 | ✅ |
| CORS_ALLOW_ORIGINS | https://your-app.azurewebsites.net | ✅ |
| GEMINI_API_KEY | your-gemini-key | ✅ |
| GEMINI_CHAT_MODEL | gemini-2.0-flash | ✅ |
| GEMINI_EMBED_MODEL | text-embedding-004 | ✅ |
| EMBED_DIM | 768 | ✅ |
| AZURE_SEARCH_ENDPOINT | your-search-endpoint | Optional |
| AZURE_SEARCH_INDEX | your-index-name | Optional |
| AZURE_SEARCH_API_KEY | your-search-key | Optional |

### 🔍 **Pre-Deployment Checklist**

- [ ] Azure Web App created
- [ ] Resource Group name noted
- [ ] Web App name noted
- [ ] Gemini API key ready
- [ ] Azure Search configured (if using search)
- [ ] Azure CLI installed and logged in

### 📊 **Post-Deployment Verification**

1. **Health Check**
   ```bash
   curl https://your-app.azurewebsites.net/healthz
   ```
   Expected: `{"status": "ok", "env": "production"}`

2. **Chat API Test**
   ```bash
   curl -X POST https://your-app.azurewebsites.net/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Test", "top_k": 6}'
   ```

3. **Monitor Logs**
   ```bash
   az webapp log tail --name your-app --resource-group your-rg
   ```

### 🏆 **Key Benefits of This Setup**

- ✅ **Clean separation**: Only bot code, no indexing
- ✅ **Azure-native**: All settings in Azure Portal
- ✅ **No .env file**: More secure configuration
- ✅ **Faster deployments**: Smaller codebase
- ✅ **Easy updates**: Change settings without redeployment
- ✅ **Production-ready**: Optimized Gunicorn config

### 🛠️ **Troubleshooting Quick Fixes**

**App not starting?**
- Check logs: `az webapp log tail --name your-app --resource-group your-rg`
- Verify startup.sh is in backend folder
- Ensure all required environment variables are set

**Import errors?**
- Check requirements.txt is in backend root
- Verify all dependencies are listed
- Check Python version compatibility (using 3.11)

**API errors?**
- Verify GEMINI_API_KEY is set correctly
- Check CORS_ALLOW_ORIGINS includes your domain
- Test with curl to isolate issues

### 📚 **Management Commands**

```bash
# View all app settings
az webapp config appsettings list --name your-app --resource-group your-rg

# Update a setting
az webapp config appsettings set --name your-app --resource-group your-rg --settings "KEY=value"

# Restart app
az webapp restart --name your-app --resource-group your-rg

# Scale app
az appservice plan update --name your-plan --resource-group your-rg --sku B2
```

---

## 🎉 Ready to Deploy!

Your backend is configured for clean, production-ready deployment to Azure Web App. The deployment will automatically:

1. Upload only the backend folder
2. Install dependencies from requirements.txt
3. Configure Gunicorn with optimal settings
4. Set all environment variables in Azure
5. Enable logging and monitoring

**Run the deployment script when ready!** 🚀
