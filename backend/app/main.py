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


@app.get("/")
async def root():
    return {"message": "PDF RAG API"}


@app.get("/health")
async def health():
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


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
    max_age=600,
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
