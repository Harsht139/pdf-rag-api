import logging
from fastapi import APIRouter, HTTPException, status, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any

from app.models.chat import ChatRequest, ChatResponse, ChatMessage, MessageRole
from app.services import chat as chat_service
from app.services.database import database_service
from app.models.document import DocumentStatus

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    chat_request: ChatRequest,
    request: Request
) -> Dict[str, Any]:
    """
    Chat endpoint that handles user queries with RAG capabilities.
    Uses the active document from the user's session.
    """
    try:
        # Get active document for the user
        active_document = await database_service.get_user_active_document(current_user["id"])
        if not active_document:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active document selected. Please select a document first."
            )
            
        # Check if document is processed
        if active_document.get("status") != DocumentStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document is not ready for querying. Current status: {active_document.get('status')}"
            )
        
        # Generate response using RAG with the active document
        response = await chat_service.generate_response(
            message=chat_request.message,
            document_id=active_document["id"],
            user_id=current_user["id"]
        )
        
        return response.dict()
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request"
        )
