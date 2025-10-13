from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Query
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import aiohttp
import os
import logging

from app.models.document import (
    DocumentCreate, 
    DocumentInDB, 
    DocumentStatus
)
from app.services.database import database_service
from app.services.storage import storage_service
from app.utils.file_utils import validate_pdf_content, download_file, process_url

logger = logging.getLogger(__name__)

# Create the router
router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentInDB, status_code=status.HTTP_201_CREATED)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file for processing
    
    This endpoint accepts PDF files and stores them in Supabase Storage.
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    try:
        logger.info(f"Processing file upload: {file.filename}")
        
        # Read file content
        content = await file.read()
        
        # Validate it's a PDF
        if not validate_pdf_content(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file"
            )
        
        # Upload to Supabase Storage
        file_url, file_path = await storage_service.upload_file(
            file_content=content, 
            filename=file.filename,
            content_type=file.content_type or "application/pdf"
        )
        
        # Save document info
        document_data = DocumentCreate(
            filename=file.filename,
            file_path=file_path,
            file_url=file_url,
            file_size=len(content),
            file_type=file.content_type or "application/pdf",
            status=DocumentStatus.COMPLETED
        )
        
        document = await database_service.create_document(document_data)
        logger.info(f"Successfully uploaded document: {document.id}")
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing file: {str(e)}"
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
            detail=f"Error listing documents: {str(e)}"
        )

@router.post("/ingest/url", response_model=DocumentInDB, status_code=status.HTTP_201_CREATED)
async def ingest_pdf_from_url(url: str = Query(..., description="URL of the PDF file to download")):
    """
    Ingest a PDF from a URL
    
    The file will be downloaded, validated as PDF, and stored in Supabase Storage.
    Supports direct PDF links and Google Drive sharing links.
    """
    try:
        logger.info(f"Processing URL: {url}")
        
        # Download the file using file_utils to handle various URL types
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Use our file_utils to handle the download
        content, filename, _ = await download_file(url, headers)
        
        # If we got here, the file was downloaded successfully
        
        # Validate it's a PDF
        if not validate_pdf_content(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The URL does not point to a valid PDF file"
            )
        
        # Upload to storage
        file_url, file_path = await storage_service.upload_file(
            file_content=content,
            filename=filename,
            content_type="application/pdf"
        )
        
        # Save document info
        document_data = DocumentCreate(
            filename=filename,
            file_path=file_path,
            file_url=file_url,
            file_size=len(content),
            file_type="application/pdf",
            status=DocumentStatus.COMPLETED
        )
        
        document = await database_service.create_document(document_data)
        logger.info(f"Successfully processed document: {document.id}")
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing URL {url}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing URL: {str(e)}"
        )
