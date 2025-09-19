import pytest
from src.rag_service import RagService

def test_process_pdf():
    rag_service = RagService()
    with open("test.pdf", "rb") as f:
        text = rag_service.process_pdf(f)
    assert text != ""  # Check if PDF text was successfully extracted