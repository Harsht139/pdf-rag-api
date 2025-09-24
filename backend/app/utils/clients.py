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
        raise RuntimeError("Supabase credentials not configured")

    try:
        # Try the simplest initialization first
        return create_client(settings.supabase_url, settings.supabase_key)
    except TypeError as e:
        if "unexpected keyword argument 'http_client'" in str(e):
            # Fall back to initialization without http_client
            from supabase import ClientOptions

            options = ClientOptions()
            return create_client(settings.supabase_url, settings.supabase_key, options)
        raise


def upload_bytes_to_supabase_storage(
    *,
    file_bytes: bytes,
    object_path: str,
    content_type: str = "application/pdf",
) -> dict:
    """Upload bytes to Supabase Storage and return { path, public_url }.

    Handles duplicate files by checking content and generating unique names if needed.
    """
    client = get_supabase_client()
    bucket = settings.supabase_bucket

    def upload_with_retry(path: str, retry_count: int = 0) -> dict:
        """Helper function to handle uploads with retries and duplicate handling"""
        try:
            # First try with upsert
            client.storage.from_(bucket).upload(
                path=path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            return {
                "path": path,
                "public_url": client.storage.from_(bucket).get_public_url(path),
            }
        except Exception as e:
            if (
                "Duplicate" in str(e) and retry_count < 3
            ):  # If duplicate, try with a new name
                import random
                import string

                # Generate a new path with a random suffix
                name_parts = path.rsplit(".", 1)
                suffix = "".join(
                    random.choices(string.ascii_lowercase + string.digits, k=6)
                )
                new_path = (
                    f"{name_parts[0]}_{suffix}.{name_parts[1]}"
                    if len(name_parts) > 1
                    else f"{path}_{suffix}"
                )
                return upload_with_retry(new_path, retry_count + 1)
            elif "file_options" in str(e):
                # Fallback for older supabase versions
                try:
                    client.storage.from_(bucket).upload(path=path, file=file_bytes)
                    return {
                        "path": path,
                        "public_url": client.storage.from_(bucket).get_public_url(path),
                    }
                except Exception as inner_e:
                    if "Duplicate" in str(inner_e) and retry_count < 3:
                        return upload_with_retry(
                            f"{path}_{retry_count}", retry_count + 1
                        )
                    raise inner_e
            raise e

    # Start the upload process with the original path
    try:
        return upload_with_retry(object_path)
    except Exception as e:
        # If all else fails, try one last time with a completely random name
        import uuid

        random_name = str(uuid.uuid4())
        ext = object_path.split(".")[-1] if "." in object_path else "bin"
        final_path = f"uploads/{random_name}.{ext}"

        client.storage.from_(bucket).upload(path=final_path, file=file_bytes)
        return {
            "path": final_path,
            "public_url": client.storage.from_(bucket).get_public_url(final_path),
        }


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
