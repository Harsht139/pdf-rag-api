from __future__ import annotations

import hashlib
import re
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from uuid import uuid4

import httpx
from app.utils.clients import (fetch_bytes_from_url, get_supabase_client,
                               upload_bytes_to_supabase_storage)
from fastapi import APIRouter, Body, File, HTTPException, UploadFile
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
async def upload_file(file: UploadFile = File(...)):
    """Case 1: Upload from device. Store to Supabase and record pending row."""
    file_bytes = await file.read()
    # Compute content hash to deduplicate
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    content_type = file.content_type or "application/pdf"
    extension = (
        file.filename.rsplit(".", 1)[-1].lower()
        if file.filename and "." in file.filename
        else "pdf"
    )

    object_path = f"uploads/{sha256}.{extension}"
    storage_info = upload_bytes_to_supabase_storage(
        file_bytes=file_bytes,
        object_path=object_path,
        content_type=content_type,
    )
    public_url = storage_info["public_url"]
    file_path = storage_info["path"]

    sb = get_supabase_client()
    # If a document with this hash already exists, return it instead of creating a duplicate
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
        "file_name": file.filename or object_path.split("/")[-1],
        "title": file.filename or object_path.split("/")[-1],
        "file_path": file_path,
        "file_size": len(file_bytes),
        "file_type": content_type,
        "source": "upload",
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
