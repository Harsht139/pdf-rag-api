from fastapi import FastAPI, UploadFile, File, HTTPException, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import io
from pydantic import BaseModel
import uuid
import httpx
import os
from urllib.parse import urlparse
from typing import Optional
from app.core.config import APP_NAME, APP_VERSION, UPLOAD_BUCKET, FRONTEND_URL
from app.services.supabase_client import supabase

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="API for handling PDF uploads and processing"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUCKET_NAME = UPLOAD_BUCKET   # Bucket name from config

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {APP_NAME} v{APP_VERSION}",
        "endpoints": {
            "root": "GET / - This page",
            "health": "GET /health - Check API health",
            "upload": "POST /upload - Upload a PDF file"
        }
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file from the local filesystem.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    try:
        file_bytes = await file.read()
        file_name = f"{uuid.uuid4()}-{file.filename}"

        # Upload to supabase bucket
        upload_response = supabase.storage.from_(BUCKET_NAME).upload(file_name, file_bytes)
        
        if isinstance(upload_response, dict) and upload_response.get("error"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=upload_response["error"]["message"]
            )

        # Get public URL and ensure it's properly formatted
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_name)
        
        # Ensure the URL is properly formatted (remove any double slashes)
        public_url = public_url.replace('//storage', '/storage') if '//storage' in public_url else public_url
        
        return {
            "message": "PDF uploaded successfully",
            "file_name": file_name,
            "public_url": public_url,
            "file_type": "upload",
            "file_size": len(file_bytes)
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


class PDFUrl(BaseModel):
    url: str


def is_valid_url(url: str) -> bool:
    """Check if the provided string is a valid URL."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def extract_filename_from_url(url: str) -> str:
    """Extract a filename from a URL."""
    parsed = urlparse(url)
    path = parsed.path
    filename = os.path.basename(path)
    
    # If no filename in URL, use a default one
    if not filename or '.' not in filename:
        return f"document-{uuid.uuid4().hex[:8]}.pdf"
    return filename


async def download_file(url: str) -> bytes:
    """Download a file from a URL."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, follow_redirects=True, timeout=30.0)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'application/pdf' not in content_type:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="URL does not point to a valid PDF file"
                )
                
            return response.content
            
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to download file from URL: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error downloading file: {str(e)}"
            )


@app.post("/upload-url")
async def upload_pdf_from_url(pdf_url: PDFUrl):
    """
    Upload a PDF from a URL.
    """
    url = pdf_url.url.strip()
    
    # Validate URL
    if not is_valid_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL provided"
        )
    
    try:
        # Download the file
        file_content = await download_file(url)
        
        # Generate a unique filename
        original_filename = extract_filename_from_url(url)
        file_name = f"{uuid.uuid4()}-{original_filename}"
        
        # Upload to Supabase
        upload_response = supabase.storage.from_(BUCKET_NAME).upload(file_name, file_content)
        
        if isinstance(upload_response, dict) and upload_response.get("error"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=upload_response["error"]["message"]
            )
        
        # Get public URL and ensure it's properly formatted
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_name)
        
        # Ensure the URL is properly formatted (remove any double slashes)
        public_url = public_url.replace('//storage', '/storage') if '//storage' in public_url else public_url
        
        # Add CORS headers to the response
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Access-Control-Allow-Headers, Authorization, X-Requested-With"
        }
        
        return {
            "message": "PDF uploaded successfully from URL",
            "file_name": file_name,
            "public_url": public_url,
            "file_type": "url",
            "file_name": file_name  # Return the filename for the proxy endpoint
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing URL: {str(e)}"
        )


@app.get("/files/{file_name}")
async def get_file(file_name: str):
    """
    Proxy endpoint to serve files from Supabase storage.
    This helps avoid CORS issues when accessing files directly.
    """
    try:
        # Download the file from Supabase
        file_data = supabase.storage.from_(BUCKET_NAME).download(file_name)
        
        if isinstance(file_data, dict) and file_data.get("error"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
            
        # Return the file with appropriate headers
        return Response(
            content=file_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={file_name}",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving file: {str(e)}"
        )
