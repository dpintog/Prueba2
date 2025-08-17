from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    
    EMBED_DIM: int = 768

    AZURE_SEARCH_ENDPOINT: str
    AZURE_SEARCH_INDEX: str
    AZURE_SEARCH_API_KEY: str | None = None
    AZURE_SEARCH_USE_MSI: bool = False

    USE_SEMANTIC_RANKER: bool = True
    SEMANTIC_CONFIG_NAME: str = "legal-semantic"
    SEMANTIC_LANGUAGE: str = "es-es"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()
