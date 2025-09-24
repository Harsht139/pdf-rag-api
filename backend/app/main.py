from app.api.v1.api import api_router
from fastapi import FastAPI
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend URL
        "http://127.0.0.1:3000",  # Frontend URL alternative
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)
