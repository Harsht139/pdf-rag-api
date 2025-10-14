import os
from typing import List
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Log environment variables (without sensitive values)
logger.info("Loading configuration from environment variables")
for var in ["SUPABASE_URL", "GOOGLE_CLOUD_PROJECT", "TASKS_QUEUE_LOCATION", 
            "TASKS_QUEUE_NAME", "SERVICE_ACCOUNT_EMAIL", "ENVIRONMENT", "SERVICE_URL"]:
    if var not in ["SUPABASE_KEY", "GEMINI_API_KEY"]:  # Skip sensitive values
        logger.debug(f"{var} = {os.getenv(var, 'Not set')}")
    else:
        logger.debug(f"{var} = {'[REDACTED]' if os.getenv(var) else 'Not set'}")

class Settings:
    def __init__(self):
        # Supabase Configuration
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_key = os.getenv("SUPABASE_KEY", "")
        self.supabase_bucket = os.getenv("SUPABASE_BUCKET", "documents")
        
        # Google Cloud Configuration
        self.google_cloud_project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
        self.tasks_queue_location = os.getenv("TASKS_QUEUE_LOCATION", "us-central1")
        self.tasks_queue_name = os.getenv("TASKS_QUEUE_NAME", "pdf-processing-queue")
        self.service_account_email = os.getenv("SERVICE_ACCOUNT_EMAIL", "")
        
        # API Configuration
        self.api_auth_token = os.getenv("API_AUTH_TOKEN", "")
        self.environment = os.getenv("ENVIRONMENT", "production")
        self.host = os.getenv("HOST", "0.0.0.0")
        self.port = int(os.getenv("PORT", "8080"))
        self.service_url = os.getenv("SERVICE_URL", "")  # e.g., https://your-service-url.run.app
        
        # CORS Configuration
        cors_origins_str = os.getenv("CORS_ORIGINS", "*")
        self.cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]
        
        # Gemini Configuration
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        
        # Set Google Application Credentials if path is provided
        google_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if google_creds_path and os.path.exists(google_creds_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_creds_path
        
        # Validate required settings
        if not self.supabase_url or not self.supabase_key:
            print("Warning: Supabase URL and Key should be set in .env file")
        if not self.google_cloud_project:
            print("Warning: GOOGLE_CLOUD_PROJECT should be set in .env file")
        if not self.gemini_api_key:
            print("Warning: GEMINI_API_KEY should be set in .env file")

# Create a singleton instance
try:
    settings = Settings()
except Exception as e:
    print(f"Error initializing settings: {e}")
    # Provide default values for testing
    settings = type('Settings', (), {
        'supabase_url': '',
        'supabase_key': '',
        'supabase_bucket': 'documents',
        'google_cloud_project': '',
        'tasks_queue_location': 'us-central1',
        'tasks_queue_name': 'pdf-processing-queue',
        'service_account_email': '',
        'api_auth_token': '',
        'environment': 'development',
        'host': '0.0.0.0',
        'port': 8080,
        'cors_origins': ['*'],
        'gemini_api_key': ''
    })()
