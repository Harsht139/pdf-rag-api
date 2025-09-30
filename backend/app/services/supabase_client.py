from supabase import create_client, Client
from app.core.config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing required Supabase configuration. Please check your .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
