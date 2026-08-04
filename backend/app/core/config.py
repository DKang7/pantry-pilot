from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "PantryPilot"
    VERSION: str = "0.1.0"
    ENV: str = "development"
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/pantrypilot"
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    GEMINI_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
