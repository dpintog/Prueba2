from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "legal-consultor"
    ENV: str = "dev"
    PORT: int = 8000
    CORS_ALLOW_ORIGINS: str = ""

    GEMINI_API_KEY: str
    GEMINI_CHAT_MODEL: str = "gemini-2.0-flash"

    AZURE_SEARCH_ENDPOINT: str
    AZURE_SEARCH_INDEX: str
    AZURE_SEARCH_API_KEY: str | None = None
    AZURE_SEARCH_USE_MSI: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()
