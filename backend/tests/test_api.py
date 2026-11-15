import os
import tempfile

# Use a distinct database and test key, before importing the application.
os.environ["NEXIS_DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.gettempdir(), "nexis_pytest_backend.db").replace("\\", "/")
os.environ["NEXIS_SECRET_KEY"] = "pytest-only-secret-key-for-local-tests"
os.environ["NEXIS_ALLOW_DOCKER"] = "false"
from fastapi.testclient import TestClient
from app.main import app
from app.core.db import Base, engine

def test_end_to_end():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        registered = client.post("/api/auth/register", json={"email": "student@example.com", "full_name": "Test Student", "password": "SecurePassword123!"})
        assert registered.status_code == 201
        assert registered.json()["role"] == "student"
        assert client.post("/api/auth/register", json={"email": "student@example.com", "full_name": "Test Student", "password": "SecurePassword123!"}).status_code == 409
        token = client.post("/api/auth/login", json={"email": "student@example.com", "password": "SecurePassword123!"}).json()["access_token"]
        h = {"Authorization": "Bearer " + token}
        assert client.get("/api/auth/me", headers=h).status_code == 200
        assert client.post("/api/challenges", headers=h, json={"title": "Secret", "description": "A test challenge here", "category": "Web", "difficulty": "Easy", "points": 100, "flag": "NEXIS{test}", "writeup": "An educational introduction to secure coding"}).status_code == 403
        assert client.get("/api/analytics/instructor/overview", headers=h).status_code == 403
        assert client.get("/api/challenges", headers=h).json() == []
        assert client.post("/api/labs/start/1", headers=h).status_code == 404