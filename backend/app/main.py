# Import routers
from app.api.v1.api import api_router
# Import config
from app.core.config import settings
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(
    title="PDF RAG API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.API_V1_STR else None,
)

# Global exception handler
from fastapi import Request
from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to catch all unhandled exceptions"""
    # Log the full traceback
    error_trace = traceback.format_exc()
    print("\n" + "=" * 50)
    print("UNHANDLED EXCEPTION")
    print("-" * 50)
    print(f"URL: {request.url}")
    print(f"Method: {request.method}")
    print(f"Error: {str(exc)}")
    print("Traceback:")
    print(error_trace)
    print("=" * 50 + "\n")
    
    # Return a 500 response with error details
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "traceback": error_trace if settings.DEBUG else None
        }
    )


@app.get("/")
async def root():
    return {"message": "PDF RAG API"}


@app.get("/health")
async def health():
    """Health check endpoint for load balancers and deployment systems"""
    return {"status": "healthy"}


@app.get("/test-cors")
async def test_cors():
    return {
        "message": "CORS test successful",
        "cors_headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    }


# Include API routers
app.include_router(api_router, prefix="/api/v1")

# CORS configuration for development
origins = [
    "http://localhost:3000",  # Default Vite dev server
    "http://127.0.0.1:3000",  # Alternative localhost
    "http://localhost:5173",  # Vite default port
    "https://your-frontend-domain.com",  # Your production frontend domain
]


# Add middleware with detailed logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    response = await call_next(request)
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    return response


# CORS configuration
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Common frontend port
    "https://your-production-domain.com",  # Your production frontend URL
]

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,  # Allow cookies in cross-origin requests
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
    max_age=600,  # How long the results of a preflight request can be cached
)


@app.post("/process_pdf")
async def process_pdf(request: Request):
    data = await request.json()
    pdf_id = data.get("pdf_id")
    pdf_url = data.get("pdf_url")

    # 1. Fetch PDF bytes from Supabase
    pdf_bytes = await fetch_bytes_from_url(pdf_url)

    # 2. Extract text
    text = extract_text(pdf_bytes)

    # 3. Optional: Chunk text to avoid token limit
    chunks = [text[i : i + 3000] for i in range(0, len(text), 3000)]

    embeddings_list = []
    for chunk in chunks:
        embeddings = generate_embeddings(chunk)  # Gemini or other API
        embeddings_list.append(embeddings)

    # 4. Store embeddings
    store_embeddings(pdf_id, embeddings_list)

    return {"status": "success", "pdf_id": pdf_id}
