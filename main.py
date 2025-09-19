from fastapi import FastAPI, UploadFile, File, HTTPException
from src.rag_service import RagService
from pydantic import BaseModel

app = FastAPI()
rag_service = RagService()

class QueryRequest(BaseModel):
    query: str

@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        text = await rag_service.process_pdf(file)
        return {"message": "PDF processed successfully", "text": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/query-pdf/")
async def query_pdf(request: QueryRequest):
    try:
        response = await rag_service.query_document(request.query)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))