# file: apps/api/tests/test_main.py
# version: 1.0.0
# date: 2025-09-23
# author: Gemini

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    """
    Test that the root endpoint is accessible and returns a welcome message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to airdeliver API"}

def test_docs_redirect():
    """
    Test that the root endpoint for docs redirects correctly.
    """
    response = client.get("/docs", follow_redirects=False)
    assert response.status_code == 307 # Temporary Redirect
