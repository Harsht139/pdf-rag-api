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

    async def get_document_by_hash(self, file_hash: str) -> Optional[DocumentInDB]:
        """
        Get a document by its file hash.
        
        Args:
            file_hash: SHA-256 hash of the file content
            
        Returns:
            DocumentInDB if found, None otherwise
        """
        try:
            result = (
                self.supabase.table("documents")
                .select("*")
                .eq("file_hash", file_hash)
                .order("created_at", desc=True)  # Get the most recent one if multiple
                .limit(1)
                .execute()
            )
            if not result.data:
                return None
            return DocumentInDB(**result.data[0])
        except Exception as e:
            logger.error(f"Error getting document by hash {file_hash}: {str(e)}")
            return None

    async def update_document_status(
        self, 
        document_id: str, 
        status: str, 
        error_message: Optional[str] = None,
        allow_missing: bool = False
    ) -> bool:
        """Update document status and error message if provided
        
        Args:
            document_id: The ID of the document to update
            status: The new status (should be a valid DocumentStatus value)
            error_message: Optional error message to store
            allow_missing: If True, don't raise an exception if document is not found
            
        Returns:
            bool: True if the update was successful, False if document not found or update failed
        """
        try:
            # First, get the current document to check its structure
            current_doc = await self.get_document(document_id)
            if not current_doc:
                msg = f"Document with ID {document_id} not found"
                if allow_missing:
                    logger.warning(f"{msg} - but continuing as allow_missing=True")
                    return False
                raise ValueError(msg)
                
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
            if allow_missing and "not found" in str(e).lower():
                return False
            raise
            
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
            
    async def search_chunks(
        self,
        document_id: str,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for document chunks using vector similarity.
        
        Args:
            document_id: The ID of the document to search within
            query_embedding: The embedding vector of the query
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1) for results
            
        Returns:
            List of matching chunks with their similarity scores
        """
        try:
            import numpy as np
            from numpy.linalg import norm
            
            # Get all chunks for the document
            chunks = await self.get_document_chunks(document_id)
            if not chunks:
                return []
                
            # Convert query embedding to numpy array
            query_embedding_np = np.array(query_embedding, dtype=np.float32)
            
            results = []
            
            for chunk in chunks:
                chunk_embedding = chunk.get('embedding')
                if not chunk_embedding:
                    continue
                    
                # Convert chunk embedding to numpy array if it's a string
                if isinstance(chunk_embedding, str):
                    try:
                        chunk_embedding = np.array(eval(chunk_embedding), dtype=np.float32)
                    except:
                        continue
                elif isinstance(chunk_embedding, list):
                    chunk_embedding = np.array(chunk_embedding, dtype=np.float32)
                
                # Calculate cosine similarity
                norm_query = norm(query_embedding_np)
                norm_chunk = norm(chunk_embedding)
                
                if norm_query == 0 or norm_chunk == 0:
                    continue
                    
                similarity = np.dot(query_embedding_np, chunk_embedding) / (norm_query * norm_chunk)
                
                if similarity >= similarity_threshold:
                    results.append({
                        'id': chunk.get('id'),
                        'document_id': chunk.get('document_id'),
                        'content': chunk.get('content', ''),
                        'metadata': chunk.get('metadata', {}),
                        'similarity': float(similarity)
                    })
            
            # Sort by similarity score in descending order
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Return top N results
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error in search_chunks: {str(e)}", exc_info=True)
            return []
            
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
            
    async def search_chunks(
        self,
        document_id: str,
        query_embedding: List[float],
        limit: int = 5,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity search
        
        Args:
            document_id: ID of the document to search within
            query_embedding: The embedding vector to search with
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score (0-1) for results
            
        Returns:
            List of matching chunks with their similarity scores
        """
        try:
            # Ensure query_embedding is a numpy array of float32
            import numpy as np
            from numpy.linalg import norm
            
            # Convert query_embedding to numpy array with float32 dtype
            query_embedding_np = np.array(query_embedding, dtype=np.float32)
            
            # Verify the document exists and is processed
            doc = await self.get_document(document_id)
            if not doc or doc.status != 'completed':
                logger.warning(f"Document {document_id} not found or not processed")
                return []
            
            # Get all chunks for the document
            chunks = await self.get_document_chunks(document_id)
            if not chunks:
                logger.warning(f"No chunks found for document {document_id}")
                return []
                
            results = []
            
            for chunk in chunks:
                try:
                    # Get chunk embedding and ensure it's a numpy array of float32
                    chunk_embedding = chunk.get('embedding')
                    if not chunk_embedding:
                        continue
                        
                    # Convert to numpy array if it's a string or list
                    if isinstance(chunk_embedding, str):
                        # Handle string representation of list
                        chunk_embedding = np.array(eval(chunk_embedding), dtype=np.float32)
                    elif isinstance(chunk_embedding, list):
                        chunk_embedding = np.array(chunk_embedding, dtype=np.float32)
                    else:
                        chunk_embedding = np.array(chunk_embedding, dtype=np.float32)
                    
                    # Calculate cosine similarity
                    norm_query = norm(query_embedding_np)
                    norm_chunk = norm(chunk_embedding)
                    
                    if norm_query == 0 or norm_chunk == 0:
                        logger.warning("Zero vector encountered in query or chunk embedding")
                        continue
                        
                    similarity = np.dot(query_embedding_np, chunk_embedding) / (norm_query * norm_chunk)
                    
                    if similarity >= similarity_threshold:
                        results.append({
                            'id': chunk.get('id'),
                            'document_id': chunk.get('document_id'),
                            'content': chunk.get('content', ''),
                            'metadata': chunk.get('metadata', {}),
                            'similarity': float(similarity)
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk.get('id')}: {str(e)}")
                    continue
                    
            # Sort by similarity in descending order
            results.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Log top results for debugging
            if results:
                logger.info(f"Top {min(3, len(results))} results with similarities: {[r['similarity'] for r in results[:3]]}")
            else:
                logger.warning("No results found above similarity threshold")
                
                # For debugging, try with a lower threshold
                if chunks:
                    logger.info("Trying with lower threshold for debugging...")
                    for chunk in chunks[:3]:  # Check first 3 chunks
                        try:
                            chunk_embedding = chunk.get('embedding')
                            if isinstance(chunk_embedding, str):
                                chunk_embedding = np.array(eval(chunk_embedding), dtype=np.float32)
                            else:
                                chunk_embedding = np.array(chunk_embedding, dtype=np.float32)
                            
                            norm_query = norm(query_embedding_np)
                            norm_chunk = norm(chunk_embedding)
                            
                            if norm_query > 0 and norm_chunk > 0:
                                similarity = np.dot(query_embedding_np, chunk_embedding) / (norm_query * norm_chunk)
                                logger.info(f"Chunk {chunk.get('id')} similarity: {similarity:.4f}, "
                                          f"content: {chunk.get('content', '')[:100]}...")
                        except Exception as e:
                            logger.error(f"Debug error: {str(e)}")
            
            return results[:limit]
            
        except Exception as e:
            error_msg = f"Error in search_chunks: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return []


# Create a singleton instance
database_service = DatabaseService()
