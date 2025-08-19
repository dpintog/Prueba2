from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    APP_NAME: str = os.getenv("APP_NAME", "Legal Bot")
    ENV: str = os.getenv("ENV", "dev")
    PORT: int = os.getenv("PORT", 8000)
    CORS_ALLOW_ORIGINS: str = os.getenv("CORS_ALLOW_ORIGINS", "")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_CHAT_MODEL: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    GEMINI_EMBED_MODEL: str = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")
    EMBED_DIM: int = os.getenv("EMBED_DIM", 768)

    AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_INDEX: str = os.getenv("AZURE_SEARCH_INDEX")
    AZURE_SEARCH_API_KEY: str | None = os.getenv("AZURE_SEARCH_API_KEY")
    AZURE_SEARCH_USE_MSI: bool = os.getenv("AZURE_SEARCH_USE_MSI", False)

    # Azure Blob Storage settings
    AZURE_BLOB_ACCOUNT_NAME: str | None = os.getenv("AZURE_BLOB_ACCOUNT_NAME")
    AZURE_BLOB_ACCOUNT_KEY: str | None = os.getenv("AZURE_BLOB_ACCOUNT_KEY")
    AZURE_BLOB_CONTAINER_NAME: str | None = os.getenv("AZURE_BLOB_CONTAINER_NAME")

    # Additional settings that might be needed
    USE_SEMANTIC_RANKER: bool = False
    SEMANTIC_CONFIG_NAME: str = "legal-semantic"
    SEMANTIC_LANGUAGE: str = "es-es"

settings = Settings()
