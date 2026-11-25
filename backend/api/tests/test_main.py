# backend/api/tests/test_main.py

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "service": "airdeliver-api",
        "environment": "development",
        "status": "ok",
    }

def test_docs_redirect():

    response = client.get("/docs", follow_redirects=False)
    assert response.status_code == 200

