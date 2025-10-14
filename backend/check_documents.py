import asyncio
import os
from dotenv import load_dotenv
from app.core.config import settings
from app.services.database import DatabaseService

async def check_documents():
    db = DatabaseService(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    # Get recent documents
    result = db.supabase.table('documents').select('*').order('created_at', desc=True).limit(5).execute()
    
    if not result.data:
        print("No documents found in the database.")
        return
    
    print("\n=== Recent Documents ===")
    for doc in result.data:
        print(f"\nDocument ID: {doc['id']}")
        print(f"Name: {doc.get('name', 'N/A')}")
        print(f"Status: {doc.get('status', 'N/A')}")
        print(f"Created: {doc.get('created_at')}")
        
        # Check if document has chunks
        chunks = db.supabase.table('document_chunks') \
            .select('id, created_at, content', count='exact') \
            .eq('document_id', doc['id']) \
            .execute()
        
        chunk_count = chunks.count if hasattr(chunks, 'count') else len(chunks.data)
        print(f"Number of chunks: {chunk_count}")
        
        if chunk_count > 0:
            # Check if chunks have embeddings
            sample_chunk = db.supabase.table('document_chunks') \
                .select('embedding') \
                .eq('document_id', doc['id']) \
                .limit(1) \
                .execute()
            
            if sample_chunk.data and 'embedding' in sample_chunk.data[0]:
                print("Chunks have embeddings: Yes")
                print(f"Embedding dimensions: {len(sample_chunk.data[0]['embedding']) if sample_chunk.data[0]['embedding'] else 0}")
            else:
                print("Chunks have embeddings: No")

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(check_documents())
