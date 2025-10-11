from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os

app = FastAPI(title="PDF RAG API")

# CORS middleware to allow frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    document_id: Optional[str] = None

# Temporary storage (replace with Supabase later)
documents_store = {}

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile):
    """Handle PDF uploads"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Only PDF files are supported")
    
    # In a real app, save to Supabase storage and process the PDF
    doc_id = f"doc_{len(documents_store) + 1}"
    documents_store[doc_id] = {
        "filename": file.filename,
        "content": "[PDF content would be processed here]"
    }
    
    return {"document_id": doc_id, "filename": file.filename}

@app.post("/api/chat")
async def chat(chat_request: ChatRequest):
    """Handle chat messages"""
    # In a real app, this would use RAG to generate a response
    last_message = chat_request.messages[-1].content
    
    return {
        "message": {
            "role": "assistant",
            "content": f"You asked about: {last_message}"
        }
    }

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
