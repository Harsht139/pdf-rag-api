from fastapi import APIRouter

# Import endpoints
from app.api.v1.endpoints import documents, chat

api_router = APIRouter()

# Include routers
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
