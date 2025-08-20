# Startup script for Azure Web App - Backend Only Deployment
# FastAPI requires a custom startup command since Azure doesn't auto-detect it

# Run FastAPI with Gunicorn from the project root (backend folder is the root)
gunicorn main:app -c gunicorn.conf.py
