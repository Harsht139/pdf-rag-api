import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Application Settings
APP_NAME = "PDF RAG API"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# File Upload Settings
UPLOAD_BUCKET = os.getenv("UPLOAD_BUCKET", "pdf-uploads")

# Frontend URL for CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
