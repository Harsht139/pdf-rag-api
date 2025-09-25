import os
from supabase import create_client, Client
from .config import settings

# Initialize Supabase client
url: str = settings.SUPABASE_URL
key: str = settings.SUPABASE_KEY
supabase: Client = create_client(url, key)
