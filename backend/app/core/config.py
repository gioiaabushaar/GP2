from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    nexis_database_url: str = "sqlite:///./nexis.db"
    nexis_secret_key: str = "unsafe-development-only-change-me"
    nexis_token_minutes: int = 120
    nexis_openai_api_key: str = ""
    nexis_openai_model: str = "gpt-4.1-mini"
    nexis_allow_docker: bool = False
    nexis_cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

settings = Settings()