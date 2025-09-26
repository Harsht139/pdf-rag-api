import os
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    PROJECT_NAME: str = "PDF RAG API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production")

    # Security
    API_KEY: str = os.getenv("API_KEY", "default-insecure-key")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    # This should match exactly with your Supabase bucket name
    SUPABASE_BUCKET: str = os.getenv("SUPABASE_BUCKET", "pdf-uploads")

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: (
            os.getenv("BACKEND_CORS_ORIGINS", "").split(",")
            if os.getenv("BACKEND_CORS_ORIGINS")
            else ["http://localhost:3000", "http://127.0.0.1:3000"]
        )
    )

    BACKEND_BASE_URL: str = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")

    # File Uploads
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default
    ALLOWED_FILE_TYPES: List[str] = os.getenv(
        "ALLOWED_FILE_TYPES", "application/pdf"
    ).split(",")

    # Google Cloud
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "")
    GCP_LOCATION: str = os.getenv("GCP_LOCATION", "us-central1")

    # Cloud Tasks
    CLOUD_TASKS_QUEUE: str = os.getenv("CLOUD_TASKS_QUEUE", "pdf-processing")
    CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL: str = os.getenv(
        "CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL", ""
    )

    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Google Cloud Project
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list"""
        return self.BACKEND_CORS_ORIGINS

    class Config:
        case_sensitive = True
        env_file = None  # Disable .env file loading
        extra = "ignore"


# Create settings instance
settings = Settings()
