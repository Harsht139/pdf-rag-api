from fastapi import FastAPI

app = FastAPI(title="PDF RAG API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "PDF RAG API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}