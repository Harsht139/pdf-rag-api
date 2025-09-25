from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # API Configuration
    PROJECT_NAME: str = "PDF RAG API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True
    ENVIRONMENT: str = "local"
    
    # Security
    API_KEY: str = "default-insecure-key"
    
    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_BUCKET: str = "documents"
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    BACKEND_BASE_URL: str = "http://localhost:8000"
    
    # File Uploads
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_FILE_TYPES: List[str] = ["application/pdf"]
    
    # Google Cloud
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "us-central1"
    
    # Cloud Tasks
    CLOUD_TASKS_QUEUE: str = "pdf-processing"
    CLOUD_TASKS_SERVICE_ACCOUNT_EMAIL: str = ""
    
    # Gemini AI
    GEMINI_API_KEY: str = ""
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = "ignore"  # This will ignore extra env vars without raising errors

# Create settings instance
settings = Settings()
