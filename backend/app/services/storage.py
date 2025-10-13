import os
from typing import Optional, Tuple
from app.config import settings
import uuid
from supabase import create_client

class StorageService:
    def __init__(self):
        self.supabase = create_client(settings.supabase_url, settings.supabase_key)
        self.bucket_name = "pdf-uploads"  # Your Supabase bucket name

    async def upload_file(
        self, file_content: bytes, filename: str, content_type: str = "application/pdf"
    ) -> Tuple[str, str]:
        """
        Upload a file to Supabase Storage
        Returns: (public_url, file_path)
        """
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
                file_options={"content-type": content_type or "application/pdf"}
            )
            
            print(f"Upload result: {result}")
            if hasattr(result, 'error'):
                print(f"Upload error: {result.error}")
            if hasattr(result, 'data'):
                print(f"Upload data: {result.data}")
            
            # Check if upload was successful
            if not result or hasattr(result, 'error') and result.error:
                error_msg = getattr(result, 'error', {}).get('message', 'Unknown error')
                raise Exception(f"Failed to upload file to Supabase Storage: {error_msg}")
            
            # Get public URL
            response = self.supabase.storage.\
                from_("pdf-uploads").\
                get_public_url(file_path)
            
            # Ensure we have a valid URL
            if not response:
                raise Exception("Failed to get public URL for uploaded file")
                
            return str(response), file_path
            
        except Exception as e:
            raise Exception(f"Failed to upload file to Supabase Storage: {str(e)}")

    async def delete_file(self, file_path: str) -> bool:
        """Delete a file from Supabase Storage"""
        try:
            self.supabase.storage.\
                from_("pdf-uploads").\
                remove([file_path])
            return True
        except Exception as e:
            raise Exception(f"Failed to delete file from Supabase Storage: {str(e)}")

    async def download_file(self, file_path: str) -> bytes:
        """Download a file from Supabase Storage"""
        try:
            response = self.supabase.storage.\
                from_("pdf-uploads").\
                download(file_path)
            return response
        except Exception as e:
            raise Exception(f"Failed to download file from Supabase Storage: {str(e)}")

# Create a singleton instance
storage_service = StorageService()
