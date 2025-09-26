import os
from typing import Optional

from supabase import Client, create_client

from .config import settings

# Initialize Supabase client (lazy initialization)
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """Get or create Supabase client with lazy initialization"""
    global _supabase_client

    if _supabase_client is None:
        url = settings.SUPABASE_URL or os.getenv("SUPABASE_URL", "")
        key = settings.SUPABASE_KEY or os.getenv("SUPABASE_KEY", "")

        if not url or not key:
            print("WARNING: Supabase URL or Key not configured. Some features may not work.")
            # Create a dummy client for development
            _supabase_client = None
        else:
            try:
                _supabase_client = create_client(url, key)
            except Exception as e:
                print(f"Warning: Could not initialize Supabase client: {e}")
                _supabase_client = None

    return _supabase_client

# For backward compatibility, create the client if env vars are available
try:
    supabase: Optional[Client] = get_supabase_client()
except Exception as e:
    print(f"Warning: Could not initialize Supabase client: {e}")
    supabase = None

# Export the function for use in other modules
__all__ = ['get_supabase_client', 'supabase']
