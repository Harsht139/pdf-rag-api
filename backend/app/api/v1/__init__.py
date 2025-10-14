from app.api.v1.endpoints import documents, process
from fastapi import APIRouter

# Create the main API router
api_router = APIRouter()

# Include the routers
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(process.router, prefix="/process", tags=["processing"])
