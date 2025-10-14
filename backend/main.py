import os
import sys
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Import routers
try:
    logger.info("Importing routers...")
    from app.api.v1.endpoints import documents, process
    logger.info("Routers imported successfully")
except Exception as e:
    logger.error(f"Error importing routers: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# Create FastAPI app with increased upload limits
try:
    logger.info("Creating FastAPI app...")
    app = FastAPI(
        title="PDF RAG API",
        description="API for uploading and processing PDF documents with RAG capabilities",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        # Increase the maximum upload file size to 50MB
        max_upload_size=50 * 1024 * 1024,  # 50MB (adjust as needed)
    )
    logger.info("FastAPI app created successfully")
except Exception as e:
    logger.error(f"Error creating FastAPI app: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# CORS middleware configuration
try:
    logger.info("Adding CORS middleware...")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for now
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    logger.info("CORS middleware added successfully")
except Exception as e:
    logger.error(f"Error adding CORS middleware: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# Include API routers with proper prefixes
try:
    logger.info("Including API routers...")
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
    app.include_router(process.router, prefix="/api/v1/process", tags=["process"])
    logger.info("API routers included successfully")
except Exception as e:
    logger.error(f"Error including API routers: {str(e)}")
    logger.error(traceback.format_exc())
    raise


# Health check endpoint
@app.get("/health")
async def health_check():
    try:
        logger.info("Health check endpoint called")
        return {"status": "ok", "service": "pdf-rag-api", "version": "1.0.0"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"status": "error", "error": "Internal server error"}
    )


# Run the application
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Starting server on port {port}")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        log_level="info",
        reload=True
    )
