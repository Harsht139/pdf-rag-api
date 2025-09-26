import os
import sys
import traceback
from typing import Optional, Dict, Any

# Try to import supabase with version check
try:
    import supabase
    from supabase import create_client, Client
    print(f"Supabase package version: {getattr(supabase, '__version__', 'Unknown')}")
except ImportError as e:
    print("ERROR: Supabase package not installed. Run: pip install supabase")
    raise

from .config import settings

# Initialize Supabase client (lazy initialization)
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """Get or create Supabase client with lazy initialization"""
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    # Get credentials from environment or settings
    url = os.getenv("SUPABASE_URL", getattr(settings, "SUPABASE_URL", ""))
    key = os.getenv("SUPABASE_KEY", getattr(settings, "SUPABASE_KEY", ""))

    # Debug info
    print("=" * 50)
    print("Initializing Supabase Client")
    print(f"Python version: {sys.version}")
    print(f"Supabase URL: {url}")
    print(f"Supabase Key present: {'Yes' if key else 'No'}")
    if key:
        print(f"Key starts with: {key[:5]}...{key[-5:] if len(key) > 10 else ''}")
    print("=" * 50)

    if not url or not key:
        print("ERROR: Missing Supabase URL or Key")
        return None

    try:
        # Try the simplest possible initialization
        print("Creating Supabase client...")
        _supabase_client = create_client(url, key)
        
        # Test the connection
        print("Testing Supabase connection...")
        try:
            # Try a simple operation
            result = _supabase_client.table('documents').select("id").limit(1).execute()
            print(f"Connection test successful: {len(result.data) if hasattr(result, 'data') else 0} documents found")
        except Exception as test_error:
            print(f"Warning: Initial connection test failed: {str(test_error)}")
            # Continue anyway, as some operations might still work
        
        return _supabase_client
        
    except Exception as e:
        print("\n" + "!" * 50)
        print("ERROR: Failed to initialize Supabase client")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Common error patterns
        if "proxy" in str(e).lower():
            print("\nFIX: Remove any proxy settings or update your Supabase client version")
        if "http" in str(e).lower():
            print("\nFIX: Check your network connection and URL")
        if "key" in str(e).lower():
            print("\nFIX: Verify your Supabase key is correct")
            
        print("\nStack trace:")
        traceback.print_exc()
        print("!" * 50 + "\n")
        
        return None


# For backward compatibility, create the client if env vars are available
try:
    supabase: Optional[Client] = get_supabase_client()
except Exception as e:
    print(f"Warning: Could not initialize Supabase client: {e}")
    supabase = None

# Export the function for use in other modules
__all__ = ["get_supabase_client", "supabase"]
