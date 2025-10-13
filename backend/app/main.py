import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
load_dotenv()

# Import API router
from app.api.v1 import api_router

# Create FastAPI app
app = FastAPI(
    title="PDF RAG API",
    description="API for uploading and processing PDF documents with RAG capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "pdf-rag-api", "version": "1.0.0"}


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True
    )
