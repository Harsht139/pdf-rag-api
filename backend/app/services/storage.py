import hashlib
import os
import uuid
from typing import Optional, Tuple, Dict, Any

from app.config import settings
from supabase import create_client


class StorageService:
    def __init__(self):
        self.supabase = create_client(settings.supabase_url, settings.supabase_key)
        self.bucket_name = "pdf-uploads"  # Your Supabase bucket name

    def _calculate_file_hash(self, file_content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        return hashlib.sha256(file_content).hexdigest()

    async def _find_duplicate_document(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """Check if a document with the same hash already exists in the database."""
        try:
            result = self.supabase.table('documents')\
                .select('*')\
                .eq('file_hash', file_hash)\
                .maybe_single()\
                .execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error checking for duplicate document: {str(e)}")
            return None

    async def upload_file(
        self, 
        file_content: bytes, 
        filename: str, 
        content_type: str = "application/pdf"
    ) -> Tuple[str, str, str]:
        """
        Upload a file to Supabase Storage if it doesn't already exist.
        
        Args:
            file_content: The file content as bytes
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            Tuple of (public_url, file_path, file_hash)
            
        Raises:
            Exception: If upload fails or file already exists
        """
        # Calculate file hash for deduplication
        file_hash = self._calculate_file_hash(file_content)
        
        # Check for existing document with same hash
        existing_doc = await self._find_duplicate_document(file_hash)
        if existing_doc:
            # Return existing file info instead of uploading again
            print(f"File already exists with ID: {existing_doc['id']}")
            return (
                existing_doc['file_url'],
                existing_doc['file_path'],
                file_hash
            )
            
        try:
            # Generate a unique filename
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = f"uploads/{unique_filename}"

            print(f"Uploading file to path: {file_path}")
            print(f"Content type: {content_type}")
            print(f"File size: {len(file_content)} bytes")

            # Get the storage bucket
            bucket = self.supabase.storage.from_("pdf-uploads")
            print(f"Using bucket: {bucket}")

            # Upload the file
            result = bucket.upload(
                path=file_path,
                file=file_content,
                file_options={"content-type": content_type or "application/pdf"},
            )

            print(f"Upload result: {result}")
            if hasattr(result, "error"):
                print(f"Upload error: {result.error}")
            if hasattr(result, "data"):
                print(f"Upload data: {result.data}")

            # Check if upload was successful
            if not result or hasattr(result, "error") and result.error:
                error_msg = getattr(result, "error", {}).get("message", "Unknown error")
                raise Exception(
                    f"Failed to upload file to Supabase Storage: {error_msg}"
                )

            # Get public URL
            response = self.supabase.storage.from_("pdf-uploads").get_public_url(
                file_path
            )

            # Ensure we have a valid URL
            if not response:
                raise Exception("Failed to get public URL for uploaded file")

            return str(response), file_path, file_hash

        except Exception as e:
            raise Exception(f"Failed to upload file to Supabase Storage: {str(e)}")

    async def delete_file(self, file_path: str, file_hash: str = None) -> bool:
        """
        Delete a file from Supabase Storage.
        
        Args:
            file_path: Path to the file in storage
            file_hash: Optional file hash to also delete from database
            
        Returns:
            bool: True if successful
        """
        # If file_hash is provided, delete the document record first
        if file_hash:
            try:
                self.supabase.table('documents')\
                    .delete()\
                    .eq('file_hash', file_hash)\
                    .execute()
            except Exception as e:
                print(f"Warning: Failed to delete document record: {str(e)}")
                
        # Then delete the file from storage
        try:
            self.supabase.storage.from_("pdf-uploads").remove([file_path])
            return True
        except Exception as e:
            raise Exception(f"Failed to delete file from Supabase Storage: {str(e)}")

    async def download_file(self, file_path: str) -> bytes:
        """Download a file from Supabase Storage"""
        try:
            response = self.supabase.storage.from_("pdf-uploads").download(file_path)
            return response
        except Exception as e:
            raise Exception(f"Failed to download file from Supabase Storage: {str(e)}")


# Create a singleton instance
storage_service = StorageService()
