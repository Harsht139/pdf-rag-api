from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_upload_pdf():
    with open("test.pdf", "rb") as f:
        response = client.post("/upload-pdf/", files={"file": f})
    assert response.status_code == 200
    assert "message" in response.json()

def test_query_pdf():
    response = client.post("/query-pdf/", json={"query": "What is the main topic?"})
    assert response.status_code == 200
    assert "response" in response.json()