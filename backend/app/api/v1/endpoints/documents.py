from __future__ import annotations

import hashlib
import re
import tempfile
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
                     UploadFile)
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
    """Case 1: Upload from device. Store to Supabase and record pending row."""
    print("\n" + "=" * 50)
    print("Starting file upload process")
    print(f"File: {file.filename}, Content-Type: {file.content_type}")

    # Log request headers for debugging
    from fastapi import Request

    try:

        # Read file content
        print("Reading file content...")
        try:
            file_bytes = await file.read()
            if not file_bytes:
                error_msg = "Error: Empty file provided"
                print(error_msg)
                raise HTTPException(status_code=400, detail=error_msg)
        except Exception as e:
            error_msg = f"Error reading file: {str(e)}"
            print(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        if not _is_pdf_bytes(file_bytes):
            raise HTTPException(status_code=400, detail="Invalid PDF file")

        # Compute file hash
        content_hash = hashlib.sha256(file_bytes).hexdigest()
        file_path = f"uploads/{content_hash}.pdf"
        public_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/{file_path}"

        # Upload to Supabase Storage directly from memory
        try:
            # First, ensure the bucket exists
            try:
                supabase.storage.get_bucket(settings.SUPABASE_BUCKET)
            except Exception as e:
                # If bucket doesn't exist, create it
                if "not found" in str(e).lower():
                    print(f"Creating bucket: {settings.SUPABASE_BUCKET}")
                    supabase.storage.create_bucket(
                        settings.SUPABASE_BUCKET,
                        {"public": True, "file_size_limit": "50MB"},
                    )
                else:
                    raise

            # Upload the file
            print(f"Uploading file to {file_path}")
            # First try to remove if exists (since upsert isn't supported)
            try:
                supabase.storage.from_(settings.SUPABASE_BUCKET).remove([file_path])
                print(f"Removed existing file at {file_path}")
            except Exception as e:
                # Ignore if file doesn't exist
                if "not found" not in str(e).lower():
                    print(f"Warning: Could not remove existing file: {e}")

            # Upload the file
            supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
                file_path, file_bytes
            )
            print(f"Successfully uploaded file to {file_path}")

        except Exception as e:
            print(f"Upload error: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file to storage: {str(e)}"
            )

        # Create new document record with only required fields
        # Let the database handle the status with its default value
        document_data = {
            "title": file.filename or "Untitled Document",
            "file_path": file_path,
            "public_url": public_url,
            "content_hash": content_hash,
            "original_filename": file.filename,
            "content_type": file.content_type,
            "file_size": len(file_bytes),
            "file_type": file.content_type,
        }

        # Only add user_id if it's not the default user and exists
        if (
            current_user
            and current_user.get("id")
            and str(current_user["id"]) != "00000000-0000-0000-0000-000000000000"
        ):
            document_data["user_id"] = str(
                current_user["id"]
            )  # Convert UUID to string for Supabase
        else:
            # Don't set user_id for default user to avoid foreign key constraint
            print("Using null user_id for default user")

        # Try to add metadata if the column exists
        try:
            # This is a test query to check if metadata column exists
            test_result = (
                supabase.from_("documents").select("metadata").limit(1).execute()
            )
            if test_result.data:
                document_data["metadata"] = {}
        except Exception:
            # If the query fails, metadata column probably doesn't exist
            print("Note: 'metadata' column not found in documents table")

        # Insert document record
        result = supabase.table("documents").insert(document_data).execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=500, detail="Failed to create document record"
            )

        document_id = result.data[0]["id"]

        # Create processing job if the table exists
        try:
            # Test if processing_jobs table exists
            test_job = supabase.table("processing_jobs").select("id").limit(1).execute()

            # If we got here, the table exists
            job_data = {
                "document_id": document_id,
                "job_type": "process_document",
                "status": "pending",
                "progress": 0,
            }

            job_result = supabase.table("processing_jobs").insert(job_data).execute()

            if not job_result.data or len(job_result.data) == 0:
                print("Warning: Failed to create processing job")
            else:
                print(f"Created processing job: {job_result.data[0]['id']}")

        except Exception as e:
            print(f"Note: Could not create processing job - {str(e)}")
            print("Continuing without processing job creation")

        return {
            "id": document_id,
            "status": "uploaded",
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
    """Mini connectivity test to Supabase Storage and DB.

    - Verifies env is present
    - Uploads a tiny test object with upsert=True
    - Removes it
    - Returns ok if successful
    """
    sb = get_supabase_client()
    # sanity check: bucket name
    from app.config import settings

    test_path = f"healthcheck/{uuid4()}.txt"
    content = b"ok"
    # upload with upsert True to avoid conflicts
    sb.storage.from_(settings.supabase_bucket).upload(
        path=test_path,
        file=content,
        file_options={"content-type": "text/plain", "upsert": True},
    )

    # try to generate a public URL and then delete the object
    public_url = sb.storage.from_(settings.supabase_bucket).get_public_url(test_path)
    sb.storage.from_(settings.supabase_bucket).remove([test_path])

    return {
        "ok": True,
        "bucket": settings.supabase_bucket,
        "test_path": test_path,
        "public_url": public_url,
    }
