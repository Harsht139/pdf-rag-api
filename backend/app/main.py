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

# CORS for local dev and frontend
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
