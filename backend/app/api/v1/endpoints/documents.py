import logging
import os
from typing import Any, Dict, List, Optional

import aiohttp
from app.models.document import DocumentCreate, DocumentInDB, DocumentStatus, DocumentResponse
from app.services.database import database_service
from app.services.storage import storage_service
from app.utils.file_utils import (download_file, process_url,
                                  validate_pdf_content)
from fastapi import (APIRouter, Depends, File, HTTPException, Query,
                     UploadFile, status, Request)
from fastapi.responses import JSONResponse
from app.api.v1.endpoints.process import process_document

logger = logging.getLogger(__name__)

# Create the router without prefix since it's already included in main.py
router = APIRouter(tags=["documents"])


@router.post(
    "/upload", response_model=DocumentInDB, status_code=status.HTTP_201_CREATED
)
async def upload_pdf(
    file: UploadFile = File(..., max_size=50 * 1024 * 1024)  # 50MB max file size
):
    """
    Upload a PDF file for processing

    This endpoint accepts PDF files and stores them in Supabase Storage.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF files are allowed"
        )

    try:
        logger.info(f"Processing file upload: {file.filename}")

        # Read file content
        content = await file.read()

        # Validate it's a PDF
        if not validate_pdf_content(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid PDF file"
            )

        # Upload to Supabase Storage (this now handles deduplication)
        file_url, file_path, file_hash = await storage_service.upload_file(
            file_content=content,
            filename=file.filename,
            content_type=file.content_type or "application/pdf",
        )

        # Check if this is a duplicate (file already existed)
        existing_doc = await database_service.get_document_by_hash(file_hash)
        if existing_doc:
            logger.info(f"Returning existing document with ID: {existing_doc.id}")
            return DocumentResponse(**existing_doc.dict())

        # Save document info with hash
        document_data = DocumentCreate(
            filename=file.filename,
            file_path=file_path,
            file_url=file_url,
            file_size=len(content),
            file_type=file.content_type or "application/pdf",
            status=DocumentStatus.PENDING,  # Will be updated by the processor
            file_hash=file_hash,
        )

        document = await database_service.create_document(document_data)
        logger.info(f"Successfully created new document: {document.id}")

        # Only trigger processing for new documents
        try:
            from app.api.v1.endpoints.process import _process_document_internal
            await _process_document_internal(str(document.id))
            logger.info(f"Triggered processing for new document: {document.id}")
        except Exception as e:
            error_msg = f"Error triggering processing for document {document.id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await database_service.update_document_status(
                document.id,
                DocumentStatus.FAILED,
                error_message=error_msg
            )

        return document

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}",
        )


@router.get("", response_model=List[DocumentInDB])
async def list_documents():
    """
    List all uploaded documents
    """
    try:
        documents = await database_service.list_documents()
        return documents
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing documents: {str(e)}",
        )


@router.post(
    "/ingest/url", response_model=DocumentInDB, status_code=status.HTTP_201_CREATED
)
async def ingest_pdf_from_url(
    url: str = Query(..., description="URL of the PDF file to download")
):
    """
    Ingest a PDF from a URL

    The file will be downloaded, validated as PDF, and stored in Supabase Storage.
    Supports direct PDF links and Google Drive sharing links.
    """
    try:
        logger.info(f"Processing URL: {url}")

        # Download the file using file_utils to handle various URL types
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Use our file_utils to handle the download
        content, filename, _ = await download_file(url, headers)

        # If we got here, the file was downloaded successfully

        # Validate it's a PDF
        if not validate_pdf_content(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The URL does not point to a valid PDF file",
            )

        # Upload to storage (handles deduplication)
        file_url, file_path, file_hash = await storage_service.upload_file(
            file_content=content, 
            filename=filename, 
            content_type="application/pdf"
        )

        # Check if this is a duplicate (file already existed)
        existing_doc = await database_service.get_document_by_hash(file_hash)
        if existing_doc:
            logger.info(f"Returning existing document with ID: {existing_doc.id}")
            return DocumentResponse(**existing_doc.dict())

        # Save document info with hash
        document_data = DocumentCreate(
            filename=filename,
            file_path=file_path,
            file_url=file_url,
            file_size=len(content),
            file_type="application/pdf",
            status=DocumentStatus.PENDING,  # Will be updated by the processor
            file_hash=file_hash,
        )

        document = await database_service.create_document(document_data)
        logger.info(f"Successfully created new document from URL: {document.id}")

        # Only trigger processing for new documents
        try:
            from app.api.v1.endpoints.process import _process_document_internal
            await _process_document_internal(str(document.id))
            logger.info(f"Triggered processing for new document: {document.id}")
        except Exception as e:
            error_msg = f"Error triggering processing for document {document.id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            await database_service.update_document_status(
                document.id,
                DocumentStatus.FAILED,
                error_message=error_msg
            )

        return DocumentResponse(**document.dict())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing URL {url}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing URL: {str(e)}",
        )
