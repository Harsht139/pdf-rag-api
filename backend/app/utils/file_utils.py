import io
import re
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import aiohttp
import PyPDF2


def validate_pdf_content(content: bytes) -> bool:
    """
    Validate if the provided content is a valid PDF file.

    Args:
        content: Binary content to validate

    Returns:
        bool: True if content is a valid PDF, False otherwise
    """
    try:
        with io.BytesIO(content) as pdf_file:
            PyPDF2.PdfReader(pdf_file)
        return True
    except (PyPDF2.errors.PdfReadError, ValueError, IndexError):
        return False


async def download_file(
    url: str, headers: Optional[Dict[str, str]] = None
) -> Tuple[bytes, str, Dict[str, Any]]:
    """
    Download a file from a URL with support for various file hosting services.

    Args:
        url: The URL of the file to download
        headers: Optional headers to include in the request

    Returns:
        Tuple of (file_content, filename, metadata)
    """
    source_type, download_url, metadata = await process_url(url)
    if source_type is None:
        source_type = "direct"

    async with aiohttp.ClientSession() as session:
        async with session.get(download_url, headers=headers) as response:
            if response.status != 200:
                raise ValueError(f"Failed to download file: HTTP {response.status}")

            content = await response.read()
            filename = get_filename_from_url(download_url, response)

            # Add response metadata
            metadata.update(
                {
                    "content_type": response.content_type,
                    "content_length": response.content_length,
                    "last_modified": response.headers.get("Last-Modified"),
                    "etag": response.headers.get("ETag"),
                }
            )

            return content, filename, metadata


async def process_url(url: str) -> Tuple[str, str, Dict[str, Any]]:
    """
    Process a URL to handle special cases like Google Drive, OneDrive, etc.

    Returns:
        Tuple of (source_type, processed_url, metadata)
    """
    metadata = {"original_url": url, "source_type": "url"}

    # Google Drive direct link
    if "drive.google.com" in url:
        return await process_google_drive_url(url, metadata)

    # OneDrive direct link
    if "onedrive.live.com" in url or "1drv.ms" in url:
        return await process_onedrive_url(url, metadata)

    # Dropbox link
    if "dropbox.com" in url:
        return await process_dropbox_url(url, metadata)

    # Default case - direct URL
    return "url", url, metadata


async def process_google_drive_url(
    url: str, metadata: Dict[str, Any]
) -> Tuple[str, str, Dict[str, Any]]:
    """Process Google Drive URL to get a direct download link"""
    file_id = None

    # Handle different Google Drive URL formats
    if "file/d/" in url:
        # Format: https://drive.google.com/file/d/FILE_ID/...
        file_id = url.split("file/d/")[1].split("/")[0]
    elif "id=" in url:
        # Format: https://drive.google.com/open?id=FILE_ID
        file_id = url.split("id=")[1].split("&")[0]

    if file_id:
        metadata.update(
            {"source_type": "google_drive", "file_id": file_id, "direct_download": True}
        )
        # Create direct download link
        direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        return "google_drive", direct_url, metadata

    return "google_drive", url, metadata


async def process_onedrive_url(
    url: str, metadata: Dict[str, Any]
) -> Tuple[str, str, Dict[str, Any]]:
    """Process OneDrive URL to get a direct download link"""
    # Convert sharing link to direct download link
    if "1drv.ms" in url:
        # Handle OneDrive short links
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True) as resp:
                url = str(resp.url)

    # Convert to direct download link
    if "redir?" in url:
        url = url.replace("redir?", "download?")
    elif "?" in url and "download" not in url:
        url = url.split("?")[0] + "?download=1"

    metadata.update({"source_type": "onedrive", "direct_download": True})

    return "onedrive", url, metadata


async def process_dropbox_url(
    url: str, metadata: Dict[str, Any]
) -> Tuple[str, str, Dict[str, Any]]:
    """Process Dropbox URL to get a direct download link"""
    # Convert to direct download link
    if "dl=0" in url:
        url = url.replace("dl=0", "dl=1")
    elif "?" not in url:
        url = f"{url}?dl=1"

    metadata.update({"source_type": "dropbox", "direct_download": True})

    return "dropbox", url, metadata


def get_filename_from_url(url: str, response: aiohttp.ClientResponse) -> str:
    """Extract filename from URL or Content-Disposition header"""
    # Try to get filename from Content-Disposition header
    content_disp = response.headers.get("Content-Disposition", "")
    if "filename=" in content_disp:
        filename = re.findall("filename=(.+)", content_disp)[0].strip("\"'")
        if filename:
            return filename

    # Extract from URL
    parsed = urlparse(url)
    filename = parsed.path.split("/")[-1]

    # Clean up the filename
    filename = re.sub(r"[^\w\-_. ]", "_", filename)

    # Add extension if missing
    if not any(
        filename.lower().endswith(ext) for ext in [".pdf", ".doc", ".docx", ".txt"]
    ):
        content_type = response.content_type
        if content_type == "application/pdf":
            filename = f"{filename}.pdf"
        elif "word" in content_type:
            filename = f"{filename}.docx"
        elif "text/plain" in content_type:
            filename = f"{filename}.txt"

    return filename or "document.pdf"
