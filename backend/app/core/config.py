import os
from pathlib import Path
from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic_settings import BaseSettings
from typing import List, Union, Optional

class Settings(BaseSettings):
    """
    Application settings model using Pydantic BaseSettings.
    Reads configuration from environment variables (case-insensitive).
    """
    PROJECT_NAME: str = "SelfDB"
    API_V1_STR: str = "/api/v1" # Base path for API version 1

    # Database configuration
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_SERVER: str = "postgres" # Docker service name
    POSTGRES_PORT: str = "5432"
    DATABASE_URL: Optional[str] = None # Allow explicit setting via env

    # Validator to assemble the DATABASE_URL from components if not explicitly set
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info) -> str:
        if v:
            # If DATABASE_URL is explicitly set in env, use it
            return v
        # Otherwise, assemble it from individual components
        # In Pydantic v2, we need to access environment variables directly
        user = os.environ.get('POSTGRES_USER')
        password = os.environ.get('POSTGRES_PASSWORD')
        server = os.environ.get('POSTGRES_SERVER', 'postgres')
        port = os.environ.get('POSTGRES_PORT', '5432')
        db = os.environ.get('POSTGRES_DB')
        if not all([user, password, db]):
             raise ValueError("Missing PostgreSQL connection details in environment variables.")
        return f"postgresql+asyncpg://{user}:{password}@{server}:{port}/{db}"

    # JWT Settings
    SECRET_KEY: str # Needs to be set in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days
    REFRESH_TOKEN_SECRET_KEY: Optional[str] = None  # Fallback to SECRET_KEY if not set

    # Storage Service Settings
    # Internal URL for backend-to-storage service communication within Docker network
    STORAGE_SERVICE_URL: str = "http://storage_service:8001"
    # External URL for generating public-facing URLs to files (via Nginx proxy)
    # Default to local storage service; overridden by STORAGE_SERVICE_EXTERNAL_URL in .env
    STORAGE_SERVICE_EXTERNAL_URL: AnyHttpUrl = "http://localhost:8001"

    # Optional Email Settings (for password reset, etc.)
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_SERVER: Optional[str] = None
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    # Default Admin Credentials
    DEFAULT_ADMIN_EMAIL: str = "admin@example.com"
    DEFAULT_ADMIN_PASSWORD: str = "adminpassword"

    # Anonymous API Key
    ANON_KEY: str

    class Config:
        # Specifies the .env file to load environment variables from
        # Load environment from project root .env
        env_file = Path(__file__).resolve().parents[3] / ".env"
        case_sensitive = True # Match environment variable names exactly

# Create a single instance of the settings to be imported across the application
settings = Settings()
