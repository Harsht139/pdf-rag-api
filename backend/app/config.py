import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the backend directory
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
    print(f"Loaded .env from: {env_path}")
else:
    print(f"Error: No .env file found at {env_path}")
    print("Please create a .env file in the backend directory with your Supabase credentials.")

class Settings:
    def __init__(self):
        # Supabase
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase URL and Key must be set in .env file")
        
        # App
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.port = int(os.getenv("PORT", 8000))

# Create a singleton instance
try:
    settings = Settings()
    print("Successfully loaded settings from .env")
    print(f"Supabase URL: {settings.supabase_url[:20]}..." if settings.supabase_url else "No Supabase URL found")
except Exception as e:
    print(f"Error loading settings: {e}")
    raise
