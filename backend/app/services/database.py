from typing import List, Optional
from supabase import create_client
from app.models.document import DocumentCreate, DocumentInDB, DocumentStatus
from app.config import settings
from datetime import datetime
import uuid

class DatabaseService:
    def __init__(self):
        self.supabase = create_client(settings.supabase_url, settings.supabase_key)
        
    async def create_document(self, document: DocumentCreate) -> DocumentInDB:
        """Create a new document record in the database"""
        try:
            document_dict = document.dict()
            document_dict['id'] = str(uuid.uuid4())
            document_dict['created_at'] = datetime.utcnow().isoformat()
            document_dict['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.supabase.table('documents').insert(document_dict).execute()
            if not result.data:
                raise Exception("Failed to create document record")
                
            return DocumentInDB(**result.data[0])
            
        except Exception as e:
            raise Exception(f"Database error: {str(e)}")
    
    async def get_document(self, document_id: str) -> Optional[DocumentInDB]:
        """Get a document by ID"""
        try:
            result = self.supabase.table('documents').select('*').eq('id', document_id).execute()
            if not result.data:
                return None
            return DocumentInDB(**result.data[0])
        except Exception as e:
            raise Exception(f"Database error: {str(e)}")
    
    async def update_document_status(
        self, document_id: str, status: DocumentStatus, error: Optional[str] = None
    ) -> bool:
        """Update document status"""
        try:
            update_data = {
                'status': status.value,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if error:
                update_data['error'] = error
                
            result = self.supabase.table('documents')\
                .update(update_data)\
                .eq('id', document_id)\
                .execute()
                
            return bool(result.data)
        except Exception as e:
            raise Exception(f"Database error: {str(e)}")
    
    async def list_documents(self) -> List[DocumentInDB]:
        """List all documents, sorted by creation date (newest first)"""
        try:
            result = self.supabase.table('documents')\
                .select('*')\
                .order('created_at', desc=True)\
                .execute()
                
            return [DocumentInDB(**doc) for doc in result.data]
        except Exception as e:
            raise Exception(f"Error listing documents: {str(e)}")

# Create a singleton instance
database_service = DatabaseService()
