import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "PantryPilot"
    VERSION: str = "0.1.0"
    ENV: str = "development"
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/pantrypilot"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
