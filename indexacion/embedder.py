from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GEMINI_API_KEY: str
    GEMINI_EMBED_MODEL: str = "text-embedding-004"
    OUTPUT_DIM: int = 768
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()
