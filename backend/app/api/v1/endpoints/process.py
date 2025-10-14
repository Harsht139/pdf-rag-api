import logging
import os
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, status, Request, Response, Depends, Header
from pydantic import BaseModel

from app.services import processing, database_service
from app.services.cloud_tasks import tasks_service
from app.models.document import DocumentStatus, DocumentInDB
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

from pydantic import BaseModel

class ProcessDocumentRequest(BaseModel):
    document_id: str

async def _process_document_internal(
    document_id: str,
    request: Optional[Request] = None,
    response: Optional[Response] = None
) -> Dict[str, Any]:
    """
    Internal function to handle document processing logic.
    Can be called from API endpoint or directly from other functions.
    """
    logger.info(f"Processing document (internal): {document_id}")
    
    # Check if document exists
    document = await database_service.get_document(document_id)
    if not document:
        error_msg = f"Document {document_id} not found"
        logger.error(error_msg)
        if response is not None:  # Only raise HTTPException if this is an API call
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )
        return {"status": "error", "message": error_msg}
    
    logger.info(f"Found document: {document.filename} (ID: {document.id})")
    
    # Get the service URL - prioritize settings.service_url
    service_url = settings.service_url.rstrip('/')
    if not service_url and request:
        # Fall back to request.base_url if service_url is not set and we have a request
        service_url = str(request.base_url).rstrip('/')
        logger.warning(f"SERVICE_URL not set in settings, falling back to request.base_url: {service_url}")
    
    if not service_url:
        error_msg = "SERVICE_URL is not configured and no request context available"
        logger.error(error_msg)
        if response is not None:  # Only raise HTTPException if this is an API call
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        return {"status": "error", "message": error_msg}
    
    # Ensure we have a proper URL
    if not service_url.startswith(('http://', 'https://')):
        service_url = f"https://{service_url}"
        
    # Construct the worker URL - ensure it matches the route definition exactly
    process_url = f"{service_url}/api/v1/process/worker"
    logger.info(f"Using worker URL: {process_url}")
    
    # Update status to QUEUED
    await database_service.update_document_status(document_id, DocumentStatus.QUEUED)
    logger.info(f"Updated document {document_id} status to QUEUED")
    
    try:
        # Create a Cloud Task
        logger.info(f"Creating Cloud Task for document {document_id}")
        task_result = await tasks_service.create_task(document_id, process_url)
        logger.info(f"Successfully created Cloud Task: {task_result}")
        
        response_data = {
            "status": "queued",
            "document_id": document_id,
            "message": "Document processing has been queued",
            "task_info": task_result
        }
        
        logger.info(f"Returning success response: {response_data}")
        return response_data
        
    except Exception as e:
        error_msg = f"Failed to create Cloud Task: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await database_service.update_document_status(
            document_id, 
            DocumentStatus.FAILED,
            error_message=error_msg
        )
        if response is not None:  # Only raise HTTPException if this is an API call
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg
            )
        return {"status": "error", "message": error_msg}

@router.post("", status_code=status.HTTP_202_ACCEPTED, include_in_schema=True)
async def process_document(
    request: Request,
    process_request: ProcessDocumentRequest,
    response: Response
) -> Dict[str, Any]:
    """
    Process a document asynchronously using Cloud Tasks.
    
    This endpoint creates a Cloud Task to process the document in the background.
    """
    document_id = process_request.document_id
    logger.info(f"[API] Received request to process document: {document_id}")
    
    try:
        return await _process_document_internal(document_id, request, response)
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        error_msg = f"Error processing document {document_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        # Update document status to failed
        await database_service.update_document_status(
            document_id, 
            DocumentStatus.FAILED,
            error_message=f"Failed to queue processing: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error queuing document processing: {str(e)}"
        )

@router.post("/worker", status_code=status.HTTP_200_OK, include_in_schema=False)
async def process_document_worker(
    request: Request,
    process_request: ProcessDocumentRequest,
    x_cloudtasks_queuename: str = Header(None, alias="X-CloudTasks-QueueName"),
    x_cloudtasks_taskname: str = Header(None, alias="X-CloudTasks-TaskName")
) -> Dict[str, Any]:
    """
    Internal endpoint called by Cloud Tasks to process a document.
    This should not be called directly by clients.
    """
    document_id = process_request.document_id
    logger.info(f"Worker received request to process document: {document_id}")
    
    try:
        # Log request details for debugging
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request body: {await request.body()}")
        
        # Verify this is coming from Cloud Tasks in production
        if settings.environment == "production" and not x_cloudtasks_queuename:
            error_msg = "Unauthorized access to worker endpoint - missing X-CloudTasks-QueueName header"
            logger.warning(error_msg)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_msg
            )
        
        logger.info(f"Processing document {document_id} from queue {x_cloudtasks_queuename} (Task: {x_cloudtasks_taskname})")
        
        # Update status to PROCESSING
        await database_service.update_document_status(
            document_id, 
            DocumentStatus.PROCESSING,
            error_message=None  # Clear any previous errors
        )
        
        try:
            # Process the document
            logger.info(f"Starting document processing for {document_id}")
            try:
                await processing.process_document(document_id)
                
                # Update status to COMPLETED
                await database_service.update_document_status(
                    document_id, 
                    DocumentStatus.COMPLETED
                )
                
                response_data = {
                    "status": "processed",
                    "document_id": document_id,
                    "message": "Document processed successfully"
                }
            except Exception as process_error:
                # Log the error and update status to FAILED
                error_msg = f"Error processing document {document_id}: {str(process_error)}"
                logger.error(error_msg, exc_info=True)
                
                try:
                    await database_service.update_document_status(
                        document_id,
                        DocumentStatus.FAILED,
                        error_message=error_msg[:500]  # Limit error message length
                    )
                except Exception as update_error:
                    logger.error(f"Failed to update document status to FAILED: {str(update_error)}")
                
                # Re-raise the original error to be handled by the outer try-except
                raise process_error
            
            logger.info(f"Successfully processed document {document_id}")
            return response_data
            
        except Exception as e:
            error_msg = f"Error processing document {document_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Update status to FAILED with error message
            await database_service.update_document_status(
                document_id,
                DocumentStatus.FAILED,
                error_message=error_msg
            )
            
            # Re-raise the exception to mark the task as failed in Cloud Tasks
            raise
            
    except HTTPException as he:
        # Log HTTP exceptions but don't retry them
        logger.error(f"HTTP error in worker: {str(he.detail)}", exc_info=True)
        raise
        
    except Exception as e:
        # Log unexpected errors
        error_msg = f"Unexpected error in worker for document {document_id}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        
        # Update status to FAILED with error message
        await database_service.update_document_status(
            document_id,
            DocumentStatus.FAILED,
            error_message=error_msg
        )
        
        # Re-raise the exception to mark the task as failed in Cloud Tasks
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )
