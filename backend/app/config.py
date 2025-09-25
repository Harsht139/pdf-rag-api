from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    supabase_url: str | None = None
    supabase_key: str | None = None
    supabase_bucket: str = "pdfs"

    gcp_project_id: str | None = None
    gcp_location: str = "us-central1"
    cloud_tasks_queue: str | None = None
    cloud_tasks_service_account_email: str | None = None

    # Base URL of this backend (e.g., Cloud Run URL) for Cloud Tasks callbacks
    backend_base_url: AnyHttpUrl | None = None
    
    gemini_api_key: str  # <-- add this
    environment: str = "local"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
