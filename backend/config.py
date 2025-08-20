from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = os.getenv("APP_NAME", "Legal Bot")
    ENV: str = os.getenv("ENV", "production")
    PORT: int = int(os.getenv("PORT", 8000))
    CORS_ALLOW_ORIGINS: str = os.getenv("CORS_ALLOW_ORIGINS", "")

    # Gemini API settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_CHAT_MODEL: str = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
    GEMINI_EMBED_MODEL: str = os.getenv("GEMINI_EMBED_MODEL", "text-embedding-004")
    EMBED_DIM: int = int(os.getenv("EMBED_DIM", 768))

    # Azure Search settings
    AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT", "")
    AZURE_SEARCH_INDEX: str = os.getenv("AZURE_SEARCH_INDEX", "")
    AZURE_SEARCH_API_KEY: str | None = os.getenv("AZURE_SEARCH_API_KEY")
    AZURE_SEARCH_USE_MSI: bool = os.getenv("AZURE_SEARCH_USE_MSI", "false").lower() == "true"

    # Azure Blob Storage settings (optional)
    AZURE_BLOB_ACCOUNT_NAME: str | None = os.getenv("AZURE_BLOB_ACCOUNT_NAME")
    AZURE_BLOB_ACCOUNT_KEY: str | None = os.getenv("AZURE_BLOB_ACCOUNT_KEY")
    AZURE_BLOB_CONTAINER_NAME: str | None = os.getenv("AZURE_BLOB_CONTAINER_NAME")

    # Additional settings
    USE_SEMANTIC_RANKER: bool = os.getenv("USE_SEMANTIC_RANKER", "false").lower() == "true"
    SEMANTIC_CONFIG_NAME: str = os.getenv("SEMANTIC_CONFIG_NAME", "legal-semantic")
    SEMANTIC_LANGUAGE: str = os.getenv("SEMANTIC_LANGUAGE", "es-es")

    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=True
    )

settings = Settings()
