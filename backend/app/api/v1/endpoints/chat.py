import logging
from fastapi import APIRouter, HTTPException, status, Request, Depends
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
from pydantic import BaseModel

from app.services import chat as chat_service
from app.services.database import database_service
from app.models.document import DocumentStatus

logger = logging.getLogger(__name__)
router = APIRouter()

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    document_id: str

class ChatResponse(BaseModel):
    message: str
    sources: List[str] = []

@router.post("", response_model=ChatResponse)
async def chat_endpoint(
    chat_request: ChatRequest,
    request: Request
) -> Dict[str, Any]:
    """
    Chat endpoint that handles user queries with RAG capabilities.
    """
    try:
        if not chat_request.messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No messages provided in the request"
            )
            
        # Get the last user message
        user_messages = [msg for msg in chat_request.messages if msg.role == 'user']
        if not user_messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No user message found in the conversation"
            )
            
        last_user_message = user_messages[-1].content
        
        # Get the document
        document = await database_service.get_document(chat_request.document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
            
        # Check if document is processed
        if document.status != DocumentStatus.COMPLETED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document is not ready for querying. Current status: {document.status}"
            )
        
        # Generate response using RAG
        response = await chat_service.generate_response(
            message=last_user_message,
            document_id=chat_request.document_id,
            user_id="anonymous"  # TODO: Replace with actual user ID from auth
        )
        
        # Ensure we're returning a dictionary that matches the ChatResponse model
        return ChatResponse(
            message=response.get('message', 'No response generated'),
            sources=response.get('sources', [])
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
