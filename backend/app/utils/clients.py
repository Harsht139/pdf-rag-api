from __future__ import annotations

import json
from typing import Optional

import httpx

try:
    from google.cloud import tasks_v2  # type: ignore
except Exception:  # Package may not be installed in local/test
    tasks_v2 = None  # type: ignore
from app.config import settings
from supabase import Client, create_client


def get_supabase_client() -> Client:
    """Create and return a Supabase client using configured credentials."""
    if not settings.supabase_url or not settings.supabase_key:
        # In tests or local without env, create a dummy client-like object that raises on use
        raise RuntimeError("Supabase credentials not configured")
    return create_client(settings.supabase_url, settings.supabase_key)


def upload_bytes_to_supabase_storage(
    *,
    file_bytes: bytes,
    object_path: str,
    content_type: str = "application/pdf",
) -> dict:
    """Upload bytes to Supabase Storage and return { path, public_url }.

    Assumes the bucket is public. If private, switch to signed URLs as needed.
    """
    client = get_supabase_client()
    bucket = settings.supabase_bucket

    # The Python client accepts bytes with a destination path
    client.storage.from_(bucket).upload(
        path=object_path,
        file=file_bytes,
        # Supabase expects header values as strings; set upsert to "true" to avoid conflicts on re-upload
        file_options={"content-type": content_type, "upsert": "true"},
    )

    public_url = client.storage.from_(bucket).get_public_url(object_path)
    return {"path": object_path, "public_url": public_url}


async def fetch_bytes_from_url(url: str) -> tuple[bytes, str]:
    """Download a file and return (content, content_type)."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
        response = await client.get(url)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "application/pdf")
        return response.content, content_type


def enqueue_process_pdf_task(*, pdf_id: str, file_url: str) -> str:
    """Create a Cloud Tasks HTTP task to trigger /process_pdf_task.

    In local/dev environments where GCP settings are missing, this is a no-op
    and returns a placeholder task name.
    """
    if tasks_v2 is None:
        return "local-task-skip"
    if not (
        settings.gcp_project_id
        and settings.cloud_tasks_queue
        and settings.backend_base_url
    ):
        return "local-task-skip"

    client = tasks_v2.CloudTasksClient()
    parent = client.queue_path(
        settings.gcp_project_id, settings.gcp_location, settings.cloud_tasks_queue
    )

    url = f"{settings.backend_base_url}/process_pdf_task"
    payload = json.dumps({"pdf_id": pdf_id, "file_url": file_url}).encode()

    task: dict = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": url,
            "headers": {"Content-Type": "application/json"},
            "body": payload,
        }
    }

    if settings.cloud_tasks_service_account_email:
        task["http_request"]["oidc_token"] = {
            "service_account_email": settings.cloud_tasks_service_account_email
        }

    response = client.create_task(parent=parent, task=task)
    return response.name
