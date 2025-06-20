import os
from pathlib import Path
from typing import Optional
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Application settings for the storage service.
    """
    PROJECT_NAME: str = "SelfDB Storage Service"
    API_V1_STR: str = "/api/v1"
    
    # JWT Settings (shared with main backend)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    
    # Storage Settings
    STORAGE_PATH: str = "/data/storage"
    
    # Base URL for constructing file URLs
    BASE_URL: AnyHttpUrl = "http://localhost"
    
    # Anonymous API Key (shared with main backend)
    ANON_KEY: Optional[str] = None
    
    # Storage Service External URL (for file access) - matches backend config
    STORAGE_SERVICE_EXTERNAL_URL: str = "http://localhost:8001"
    
    class Config:
        # Automatically locate the .env file at the project root
        env_file = Path(__file__).resolve().parents[3] / ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()
