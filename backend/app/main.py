from app.api.v1.api import api_router
from app.utils.clients import fetch_bytes_from_url
from app.utils.pdf_processing import (extract_text, generate_embeddings,
                                      store_embeddings)
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PDF RAG API", version="1.0.0")


@app.get("/")
async def root():
    return {"message": "PDF RAG API"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


app.include_router(api_router, prefix="/api/v1")

# CORS configuration
origins = [
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",  # React dev server alternative
    # "https://your-frontend-domain.com",  # Add when deployed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # use only this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
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
