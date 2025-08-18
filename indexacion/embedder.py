from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Gemini settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    GEMINI_EMBED_MODEL: str = os.getenv("GEMINI_EMBED_MODEL")
    OUTPUT_DIM: int = int(os.getenv("EMBED_DIM", 768))
    
    # Azure AI Search settings
    AZURE_SEARCH_ENDPOINT: str = os.getenv("AZURE_SEARCH_ENDPOINT")
    AZURE_SEARCH_INDEX: str = os.getenv("AZURE_SEARCH_INDEX")
    AZURE_SEARCH_API_KEY: str = os.getenv("AZURE_SEARCH_API_KEY", "")
    AZURE_SEARCH_USE_MSI: bool = os.getenv("AZURE_SEARCH_USE_MSI", "false").lower() == "true"
    
    # Azure Blob Storage settings
    AZURE_BLOB_ACCOUNT_NAME: str = os.getenv("AZURE_BLOB_ACCOUNT_NAME")
    AZURE_BLOB_ACCOUNT_KEY: str = os.getenv("AZURE_BLOB_ACCOUNT_KEY")
    AZURE_BLOB_CONTAINER_NAME: str = os.getenv("AZURE_BLOB_CONTAINER_NAME")

settings = Settings()
