import os
import asyncio
from app.core.config import settings
from app.services.database import DatabaseService

async def run_migration():
    db_service = DatabaseService(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    # Read the migration file
    with open('migrations/20231014_add_vector_extension_and_function.sql', 'r') as f:
        sql = f.read()
    
    # Execute the SQL
    try:
        # Split into individual statements
        statements = [s.strip() for s in sql.split(';') if s.strip()]
        
        for stmt in statements:
            if stmt:  # Skip empty statements
                print(f"Executing: {stmt[:100]}...")
                result = db_service.supabase.rpc('execute_sql', {'query': stmt}).execute()
                print(f"Result: {result}")
                
    except Exception as e:
        print(f"Error executing migration: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())
