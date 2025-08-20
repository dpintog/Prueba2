import os

# Azure Web App Configuration - Backend Only Deployment
bind = "0.0.0.0:" + str(os.environ.get("PORT", 8000))
workers = int(os.environ.get("WORKERS", 2))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = int(os.environ.get("TIMEOUT", 120))

# Logging configuration for Azure
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Optimize for Azure
max_requests = 1000
max_requests_jitter = 100
preload_app = True
keepalive = 2
