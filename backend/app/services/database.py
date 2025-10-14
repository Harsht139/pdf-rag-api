import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

from app.config import settings
from app.models.document import DocumentCreate, DocumentInDB, DocumentStatus
from supabase import create_client

# Set up logging
logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self):
        self.supabase = create_client(settings.supabase_url, settings.supabase_key)
        self._lock = asyncio.Lock()

    async def create_document(self, document: DocumentCreate) -> DocumentInDB:
        """Create a new document record in the database"""
        try:
            async with self._lock:
                document_dict = document.dict()
                document_dict["id"] = str(uuid.uuid4())
                document_dict["created_at"] = datetime.utcnow().isoformat()
                document_dict["updated_at"] = datetime.utcnow().isoformat()

                # Use a thread pool to run the synchronous Supabase client
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self.supabase.table("documents").insert(document_dict).execute()
                )
                
                if not result.data:
                    raise Exception("Failed to create document record")

                return DocumentInDB(**result.data[0])

        except Exception as e:
            raise Exception(f"Database error: {str(e)}")

    async def get_document(self, document_id: str) -> Optional[DocumentInDB]:
        """Get a document by ID"""
        try:
            result = (
                self.supabase.table("documents")
                .select("*")
                .eq("id", document_id)
                .execute()
            )
            if not result.data:
                return None
            return DocumentInDB(**result.data[0])
        except Exception as e:
            raise Exception(f"Database error: {str(e)}")

    async def update_document_status(
        self, 
        document_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ) -> bool:
        """Update document status and error message if provided
        
        Args:
            document_id: The ID of the document to update
            status: The new status (should be a valid DocumentStatus value)
            error_message: Optional error message to store
            
        Returns:
            bool: True if the update was successful, False otherwise
            
        Raises:
            Exception: If there's an error updating the document
        """
        try:
            # First, get the current document to check its structure
            current_doc = await self.get_document(document_id)
            if not current_doc:
                raise ValueError(f"Document with ID {document_id} not found")
                
            # Prepare the update data
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Only include error_message if it's provided and the column exists
            if error_message is not None:
                update_data["error_message"] = error_message
            
            # Log the update
            logger.info(f"Updating document {document_id} status to {status}")
            if error_message:
                logger.warning(f"Error message for document {document_id}: {error_message[:200]}...")
            
            # Execute the update
            result = (
                self.supabase.table("documents")
                .update(update_data)
                .eq("id", document_id)
                .execute()
            )
            
            if not result.data:
                logger.error(f"No data returned when updating document {document_id}")
                return False
                
            logger.info(f"Successfully updated document {document_id} status to {status}")
            return True
            
        except Exception as e:
            error_msg = f"Error updating document status for {document_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)
            
    async def create_chunk(
        self, 
        document_id: str, 
        content: str, 
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new chunk for a document"""
        try:
            chunk_data = {
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "content": content,
                "embedding": embedding,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            result = self.supabase.table("document_chunks").insert(chunk_data).execute()
            if not result.data:
                raise Exception("Failed to create chunk record")
                
            return result.data[0]
            
        except Exception as e:
            raise Exception(f"Error creating chunk: {str(e)}")
            
    async def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document"""
        try:
            result = (
                self.supabase.table("document_chunks")
                .select("*")
                .eq("document_id", document_id)
                .order("chunk_number")
                .execute()
            )
            return result.data
        except Exception as e:
            raise Exception(f"Error getting document chunks: {str(e)}")

    async def delete_document_chunks(self, document_id: str) -> bool:
        """Delete all chunks for a document"""
        try:
            result = (
                self.supabase.table("document_chunks")
                .delete()
                .eq("document_id", document_id)
                .execute()
            )
            return True
        except Exception as e:
            raise Exception(f"Error deleting document chunks: {str(e)}")
            
    async def list_documents(self) -> List[DocumentInDB]:
        """List all documents"""
        try:
            print("Attempting to list documents from Supabase...")
            print(f"Supabase URL: {settings.supabase_url}")
            
            # Get the documents
            response = self.supabase.table("documents").select("*").order("created_at", desc=True).execute()
            print(f"Supabase response: {response}")
            
            if not hasattr(response, 'data'):
                print("No 'data' attribute in response")
                return []
                
            documents = response.data
            print(f"Found {len(documents)} documents in response")
            
            # Convert to Pydantic models
            result = []
            for doc in documents:
                try:
                    result.append(DocumentInDB(**doc))
                except Exception as e:
                    print(f"Error converting document {doc.get('id')} to DocumentInDB: {str(e)}")
                    print(f"Problematic document data: {doc}")
            
            print(f"Successfully converted {len(result)} documents to DocumentInDB models")
            return result
            
        except Exception as e:
            print(f"Error in list_documents: {str(e)}", exc_info=True)
            raise Exception(f"Error listing documents: {str(e)}")


# Create a singleton instance
database_service = DatabaseService()
