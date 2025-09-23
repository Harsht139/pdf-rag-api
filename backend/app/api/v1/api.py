from app.api.v1.endpoints import documents
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(documents.router, tags=["documents"])
