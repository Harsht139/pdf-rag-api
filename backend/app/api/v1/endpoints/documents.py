from __future__ import annotations

import hashlib
import re
import tempfile
import traceback
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from uuid import uuid4

import httpx
from app.api.v1.dependencies import get_current_user
# Local imports
from app.core.config import settings
from app.core.supabase import supabase
from app.utils.clients import (fetch_bytes_from_url, get_supabase_client,
                               upload_bytes_to_supabase_storage)
from fastapi import (APIRouter, Body, Depends, File, HTTPException, Request,
                     UploadFile, status)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

router = APIRouter()


class UrlPayload(BaseModel):
    pdf_url: HttpUrl


def _derive_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = parsed.path.rsplit("/", 1)[-1] or "document.pdf"
    return name


def _safe_insert_document(payload: dict) -> None:
    sb = get_supabase_client()
    try:
        sb.table("documents").insert(payload).execute()
    except Exception:
        minimal = {
            "id": payload["id"],
            "status": payload["status"],
            "title": payload.get("title") or payload.get("file_name") or "document.pdf",
            "file_path": payload["file_path"],
        }
        sb.table("documents").insert(minimal).execute()


async def _resolve_download_url(url: str) -> str:
    """Turn common share links into direct-download URLs and validate support.

    Supports:
    - Direct .pdf links
    - Google Drive share links
    - Dropbox share links
    Otherwise: attempts HEAD to verify PDF. If not PDF, raises 400.
    """
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path

    # Google Drive patterns
    if "drive.google.com" in netloc:
        # /file/d/<id>/view?...  -> uc?export=download&id=<id>
        m = re.search(r"/file/d/([^/]+)/", path)
        file_id = None
        if m:
            file_id = m.group(1)
        else:
            qs = parse_qs(parsed.query)
            file_id = qs.get("id", [None])[0]
        if file_id:
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        raise HTTPException(
            status_code=400, detail="Unsupported Google Drive link format."
        )

    # Dropbox share -> direct download
    if "dropbox.com" in netloc:
        # Convert www.dropbox.com/s/...?... -> dl.dropboxusercontent.com/s/... and dl=1
        new_netloc = "dl.dropboxusercontent.com"
        qs = parse_qs(parsed.query)
        qs["dl"] = ["1"]
        new_query = urlencode({k: v[-1] for k, v in qs.items()})
        direct = urlunparse((parsed.scheme, new_netloc, path, "", new_query, ""))
        return direct

    # OneDrive public link -> force download
    if "1drv.ms" in netloc or "onedrive.live.com" in netloc:
        # Append download=1 to query if not present
        qs = parse_qs(parsed.query)
        qs["download"] = ["1"]
        new_query = urlencode({k: v[-1] for k, v in qs.items()})
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, "", new_query, "")
        )

    # GitHub file links -> raw
    if "github.com" in netloc:
        parts = path.strip("/").split("/")
        if len(parts) >= 5 and parts[2] == "blob":
            owner, repo, _, branch = parts[:4]
            raw_path = "/".join(parts[4:])
            return (
                f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{raw_path}"
            )

    # Direct .pdf path
    if path.lower().endswith(".pdf"):
        return url

    # Fallback: HEAD request to check content-type
    # Try HEAD: if content-type is pdf, accept
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resp = await client.head(url)
            if resp.status_code < 400:
                ct = resp.headers.get("content-type", "").lower()
                if "pdf" in ct:
                    return url
    except Exception:
        pass

    # Generic webpage: try to find a PDF link in HTML
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
            m = re.search(r"href=[\"\']([^\"\']+\.pdf)(?:[\"\'])", html, re.IGNORECASE)
            if m:
                found = m.group(1)
                # Resolve relative URLs
                if found.startswith("http://") or found.startswith("https://"):
                    return found
                else:
                    base = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))
                    if found.startswith("/"):
                        return base + found
                    else:
                        base_path = "/".join(parsed.path.split("/")[:-1])
                        return base + "/" + base_path.strip("/") + "/" + found
    except Exception:
        pass

    raise HTTPException(
        status_code=400,
        detail="Unsupported link type. Provide a direct PDF or a public Drive/Dropbox/OneDrive/GitHub link, or upload the file.",
    )


def _is_pdf_bytes(data: bytes) -> bool:
    return data.startswith(b"%PDF-")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...), current_user: dict = Depends(get_current_user)
):
    """
    Handle file uploads to Supabase storage.
    
    Args:
        file: The uploaded file
        current_user: Authenticated user info from JWT token
        
    Returns:
        dict: Upload result with file details
        
    Raises:
        HTTPException: If there's an error processing the upload
    """
    # Log the start of the upload process
    print("\n" + "=" * 50)
    print(f"Starting file upload for: {file.filename}")
    print(f"Content type: {file.content_type}")
    print(f"Current user: {current_user.get('email') if current_user else 'None'}")
    
    try:
        # Validate file
        if not file.filename:
            error_msg = "No filename provided"
            print(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=error_msg
            )
            
        if not file.filename.lower().endswith(".pdf"):
            error_msg = f"Invalid file type. Only PDF files are supported. Got: {file.filename}"
            print(error_msg)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=error_msg
            )
        
        # Read file content
        try:
            file_bytes = await file.read()
            print(f"Read {len(file_bytes)} bytes from file")
            
            if not file_bytes:
                error_msg = "Error: Empty file provided"
                print(error_msg)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=error_msg
                )
                
            if not _is_pdf_bytes(file_bytes):
                error_msg = "Invalid PDF file: File does not start with PDF header"
                print(error_msg)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=error_msg
                )
                
        except Exception as e:
            error_msg = f"Error reading file: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())  # Log full traceback
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"File processing error: {str(e)}"
            )
            
        # If we get here, we have valid file content
        print("File validation successful")
        
        # Initialize Supabase client
        supabase_client = get_supabase_client()
        if not supabase_client:
            error_msg = "Failed to initialize Supabase client. Check your SUPABASE_URL and SUPABASE_KEY environment variables."
            print(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )

        # Compute file hash
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        file_path = f"uploads/{content_hash}.pdf"
        public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{file_path}"

        # Upload to Supabase Storage directly from memory
        try:
            # Get the storage bucket
            storage = supabase_client.storage.from_(settings.SUPABASE_BUCKET)
            
            # Upload the file
            print(f"Uploading file to {file_path}")
            
            # Upload the file with content type
            try:
                # First, make sure the uploads folder exists
                try:
                    # This will create the folder if it doesn't exist
                    uploads_path = "uploads"
                    upload_response = storage.upload(
                        path=f"{uploads_path}/.keep",
                        file=b"",  # Empty file to create the folder
                        file_options={"content-type": "text/plain"}
                    )
                    print(f"Created uploads folder: {upload_response}")
                except Exception as folder_error:
                    print(f"Note: Could not create uploads folder (may already exist): {folder_error}")
                
                # Now upload the actual file
                upload_response = storage.upload(
                    path=file_path, 
                    file=file_bytes,
                    file_options={"content-type": "application/pdf"}
                )
                print(f"Upload response: {upload_response}")
                
                # Get public URL
                public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{file_path}"
                
                # Create a signed URL (optional)
                signed_url = None
                try:
                    signed_url = storage.create_signed_url(
                        file_path, 
                        60 * 60 * 24 * 7  # 1 week
                    )
                    print(f"Created signed URL: {signed_url}")
                except Exception as sign_error:
                    print(f"Warning: Could not create signed URL: {sign_error}")
                    # Continue without signed URL
                
                print(f"Successfully uploaded file to {file_path}")
                
                # Create document record in database
                document_data = {
                    "file_name": file.filename,
                    "file_path": file_path,
                    "file_size": len(file_bytes),
                    "content_hash": content_hash,
                    "uploaded_by": current_user.get("id") if current_user else None,
                    "status": "uploaded",
                    "public_url": public_url,
                    "signed_url": signed_url,
                }
                
                try:
                    # Insert the document record
                    result = supabase_client.table("documents").insert(document_data).execute()
                    print(f"Document record created: {result}")
                    
                    # Return success response
                    return {
                        "status": "success",
                        "message": "File uploaded successfully",
                        "document_id": result.data[0]["id"] if result.data else None,
                        "file_path": file_path,
                        "public_url": public_url,
                        "signed_url": signed_url,
                    }
                    
                except Exception as db_error:
                    error_msg = f"Database error: {str(db_error)}"
                    print(error_msg)
                    print(traceback.format_exc())
                    
                    # Even if database fails, return success since file was uploaded
                    return {
                        "status": "partial_success",
                        "message": "File uploaded but failed to save document record",
                        "file_path": file_path,
                        "public_url": public_url,
                        "signed_url": signed_url,
                        "error": str(db_error)
                    }
                
            except Exception as upload_error:
                error_msg = f"Failed to upload file to storage: {str(upload_error)}"
                print(error_msg)
                print(traceback.format_exc())
                
                # Check if it's an RLS error
                if "row-level security" in str(upload_error).lower():
                    return {
                        "status": "error",
                        "message": "Permission denied by Row Level Security (RLS) policies",
                        "solution": [
                            "1. Go to your Supabase Dashboard",
                            "2. Navigate to Storage > Policies",
                            f"3. For the '{settings.SUPABASE_BUCKET}' bucket, add a policy that allows uploads",
                            "4. For development, you can use a policy that allows all operations with: `true`"
                        ]
                    }
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to upload file to storage: {str(upload_error)}"
                )
                
        except Exception as e:
            error_msg = f"Error during file upload process: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error during file upload process: {str(e)}"
            )
            
        # Create processing job if the table exists
        try:
            # Test if processing_jobs table exists
            test_job = supabase_client.table("processing_jobs").select("id").limit(1).execute()

            # If we got here, the table exists
            job_data = {
                "document_id": document["id"],
                "job_type": "process_document",
                "status": "pending",
                "progress": 0,
            }

            job_result = supabase_client.table("processing_jobs").insert(job_data).execute()

            if not job_result.data or len(job_result.data) == 0:
                print("Warning: Failed to create processing job")
            else:
                print(f"Created processing job: {job_result.data[0]['id']}")

        except Exception as e:
            print(f"Note: Could not create processing job - {str(e)}")
            print("Continuing without processing job creation")
            print(traceback.format_exc())

        return {
            "id": document["id"],
            "status": "processing",
            "job_id": job_result.data[0]["id"] if job_result.data else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")
    finally:
        print("=" * 50 + "\n")


@router.post("/upload_link")
async def upload_link(payload: UrlPayload = Body(...)):
    """Case 2: Upload via link. Download, store, and record pending row."""
    direct_url = await _resolve_download_url(str(payload.pdf_url))
    try:
        file_bytes, content_type = await fetch_bytes_from_url(direct_url)
    except Exception:
        raise HTTPException(status_code=400, detail="Cannot fetch PDF")
    file_name = _derive_filename_from_url(direct_url)

    # Compute content hash for deduplication
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    # Validate PDF magic header
    if not _is_pdf_bytes(file_bytes):
        raise HTTPException(status_code=400, detail="Fetched file is not a valid PDF")

    object_path = f"uploads/{sha256}.pdf"
    storage_info = upload_bytes_to_supabase_storage(
        file_bytes=file_bytes,
        object_path=object_path,
        content_type=content_type,
    )
    public_url = storage_info["public_url"]
    file_path = storage_info["path"]

    sb = get_supabase_client()

    # Return existing document if this content was seen before
    existing = (
        sb.table("documents")
        .select("id,status,file_path,public_url")
        .eq("content_hash", sha256)
        .limit(1)
        .execute()
    )
    if getattr(existing, "data", None):
        row = existing.data[0]
        return {
            "document_id": row["id"],
            "status": row.get("status", "ready"),
            "file_path": row.get("file_path"),
            "public_url": row.get("public_url"),
            "deduplicated": True,
        }

    doc_id = str(uuid4())
    insert_payload = {
        "id": doc_id,
        "status": "processing",
        "file_name": file_name,
        "title": file_name,
        "file_path": file_path,
        "file_size": len(file_bytes),
        "file_type": content_type,
        "source": "url",
        "chunk_count": 0,
        "content_hash": sha256,
        "public_url": public_url,
    }
    _safe_insert_document(insert_payload)

    return {
        "document_id": doc_id,
        "status": "processing",
        "file_path": file_path,
        "public_url": public_url,
    }


# Processing endpoints intentionally omitted for now.


@router.get("/storage_check")
async def storage_check():
    """Mini connectivity test to Supabase Storage.
    
    This test verifies that we can connect to Supabase Storage
    and access the configured bucket.
    """
    try:
        sb = get_supabase_client()
        if not sb:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize Supabase client. Check your SUPABASE_URL and SUPABASE_KEY."
            )
            
        # Get the bucket name from settings
        bucket = settings.SUPABASE_BUCKET
        if not bucket:
            raise HTTPException(
                status_code=500,
                detail="SUPABASE_BUCKET is not configured in settings"
            )
            
        # Try to access the bucket directly
        try:
            # This will use the bucket name directly without trying to list all buckets first
            storage = sb.storage.from_(bucket)
            
            # Try to get the public URL of a test path
            test_path = f"healthcheck/test-{uuid4()}.txt"
            public_url = storage.get_public_url(test_path)
            
            # If we got this far, the connection is working
            return {
                "status": "success",
                "message": "Successfully connected to Supabase Storage",
                "bucket": bucket,
                "public_url_example": public_url,
                "note": "The public URL may not work until you upload a file to that path"
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"Error accessing bucket: {error_msg}")
            
            # Check for specific error cases
            if "Bucket not found" in error_msg:
                return {
                    "status": "error",
                    "message": f"Bucket '{bucket}' not found in Supabase Storage",
                    "suggestion": [
                        "1. Go to your Supabase Dashboard",
                        "2. Navigate to Storage",
                        "3. Create a bucket named exactly as specified in your configuration"
                    ]
                }
            elif "row-level security" in error_msg.lower():
                return {
                    "status": "rls_error",
                    "message": "Row Level Security (RLS) is preventing access",
                    "bucket": bucket,
                    "solution": [
                        "1. Go to your Supabase Dashboard",
                        "2. Navigate to Authentication > Policies",
                        f"3. Find the policies for the '{bucket}' bucket",
                        "4. Add a policy to allow the required operations"
                    ]
                }
            
        except Exception as e:
            error_msg = f"Error accessing bucket '{bucket}': {str(e)}"
            print(error_msg)
            
            # Check if this is an RLS issue
            if "row-level security" in str(e).lower():
                return {
                    "status": "rls_error",
                    "message": "Row Level Security (RLS) is enabled on your Supabase Storage",
                    "bucket": bucket,
                    "solution": [
                        "1. Go to your Supabase Dashboard",
                        "2. Navigate to Authentication > Policies",
                        f"3. Find the policies for the '{bucket}' bucket",
                        "4. Add a policy to allow public access or adjust your RLS rules",
                        "OR",
                        "Use the Supabase service_role key (not recommended for production)"
                    ]
                }
            
            raise HTTPException(
                status_code=500,
                detail=error_msg
            )
            
    except Exception as e:
        error_msg = f"Storage check failed: {str(e)}"
        print(error_msg)
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=error_msg
        )
