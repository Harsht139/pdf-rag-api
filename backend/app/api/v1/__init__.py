from fastapi import APIRouter
from app.api.v1.endpoints import documents

# Create the main API router
api_router = APIRouter()

# Include the documents router
api_router.include_router(documents.router)
