import os
import tempfile
from datetime import datetime, timedelta, timezone

import jwt

# Use a distinct database and test key before importing the application.
os.environ["NEXIS_DATABASE_URL"] = (
    "sqlite:///" + os.path.join(
        tempfile.gettempdir(),
        "nexis_pytest_backend.db"
    ).replace("\\", "/")
)
os.environ["NEXIS_SECRET_KEY"] = "pytest-only-secret-key-for-local-tests"
os.environ["NEXIS_ALLOW_DOCKER"] = "false"

from fastapi.testclient import TestClient
from app.main import app
from app.core.db import Base, engine, SessionLocal
from app.core.models import User
from app.core.security import hash_password, make_token


def test_end_to_end():
    Base.metadata.drop_all(bind=engine)

    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"

        registered = client.post(
            "/api/auth/register",
            json={
                "email": "student@example.com",
                "full_name": "Test Student",
                "password": "SecurePassword123!"
            }
        )

        assert registered.status_code == 201
        assert registered.json()["role"] == "student"
		        # Prevent self-assignment of instructor role
        attempted_escalation = client.post(
            "/api/auth/register",
            json={
                "email": "attacker@example.com",
                "full_name": "Attempted Instructor",
                "password": "SecurePassword123!",
                "role": "instructor"
            }
        )

        assert attempted_escalation.status_code == 201
        assert attempted_escalation.json()["role"] == "student"

        duplicate = client.post(
            "/api/auth/register",
            json={
                "email": "student@example.com",
                "full_name": "Test Student",
                "password": "SecurePassword123!"
            }
        )
        assert duplicate.status_code == 409

        token = client.post(
            "/api/auth/login",
            json={
                "email": "student@example.com",
                "password": "SecurePassword123!"
            }
        ).json()["access_token"]

        h = {"Authorization": "Bearer " + token}

        assert client.get("/api/auth/me", headers=h).status_code == 200

        user_id = str(registered.json()["id"])
        secret = os.environ["NEXIS_SECRET_KEY"]

        # Missing token
        assert client.get("/api/auth/me").status_code == 401

        # Invalid token
        assert client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.token.value"}
        ).status_code == 401

        # Expired token
        expired_token = jwt.encode(
            {
                "sub": user_id,
                "exp": datetime.now(timezone.utc) - timedelta(minutes=1)
            },
            secret,
            algorithm="HS256"
        )

        assert client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        ).status_code == 401

        # Token without sub
        token_without_sub = jwt.encode(
            {
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5)
            },
            secret,
            algorithm="HS256"
        )

        assert client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token_without_sub}"}
        ).status_code == 401

        # Token without exp
        token_without_exp = jwt.encode(
            {"sub": user_id},
            secret,
            algorithm="HS256"
        )

        assert client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token_without_exp}"}
        ).status_code == 401

        # Student permissions
        assert client.post(
            "/api/challenges",
            headers=h,
            json={
                "title": "Secret",
                "description": "A test challenge here",
                "category": "Web",
                "difficulty": "Easy",
                "points": 100,
                "flag": "NEXIS{test}",
                "writeup": "An educational introduction to secure coding"
            }
        ).status_code == 403

        assert client.get(
            "/api/analytics/instructor/overview",
            headers=h
        ).status_code == 403

        assert client.get(
            "/api/challenges",
            headers=h
        ).json() == []

        assert client.post(
            "/api/labs/start/1",
            headers=h
        ).status_code == 404
        # Create an instructor in the test database
        with SessionLocal() as db:
            instructor_user = User(
                email="instructor@example.com",
                full_name="Test Instructor",
                password_hash=hash_password("InstructorPassword123!"),
                role="instructor"
            )

            db.add(instructor_user)
            db.commit()
            db.refresh(instructor_user)

            instructor_token = make_token(instructor_user)

        instructor_headers = {
            "Authorization": f"Bearer {instructor_token}"
        }

        # Instructor creates a challenge
        instructor_challenge = client.post(
            "/api/challenges",
            headers=instructor_headers,
            json={
                "title": "Instructor Test",
                "description": "Testing instructor permissions",
                "category": "Web",
                "difficulty": "Easy",
                "points": 100,
                "flag": "NEXIS{instructor_test}",
                "writeup": "This is a test writeup for instructor permissions."
            }
        )

        assert instructor_challenge.status_code == 201

        # Instructor accesses analytics
        overview = client.get(
            "/api/analytics/instructor/overview",
            headers=instructor_headers
        )

        assert overview.status_code == 200
        assert overview.json()["challenges"] == 1