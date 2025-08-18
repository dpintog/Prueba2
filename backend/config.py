from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path

# Get the parent directory (project root) to find .env file
BASE_DIR = Path(__file__).parent.parent
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):
    APP_NAME: str = "legal-consultor"
    ENV: str = "dev"
    PORT: int = 8000
    CORS_ALLOW_ORIGINS: str = ""

    GEMINI_API_KEY: str
    GEMINI_CHAT_MODEL: str = "gemini-2.0-flash"
    GEMINI_EMBED_MODEL: str = "text-embedding-004"
    EMBED_DIM: int = 768

    AZURE_SEARCH_ENDPOINT: str
    AZURE_SEARCH_INDEX: str
    AZURE_SEARCH_API_KEY: str | None = None
    AZURE_SEARCH_USE_MSI: bool = False

    # Azure Blob Storage settings
    AZURE_BLOB_ACCOUNT_NAME: str | None = None
    AZURE_BLOB_ACCOUNT_KEY: str | None = None
    AZURE_BLOB_CONTAINER_NAME: str | None = None

    # Additional settings that might be needed
    USE_SEMANTIC_RANKER: bool = False
    SEMANTIC_CONFIG_NAME: str = "legal-semantic"
    SEMANTIC_LANGUAGE: str = "es-es"

    model_config = SettingsConfigDict(env_file=str(ENV_FILE), case_sensitive=False)

settings = Settings()
