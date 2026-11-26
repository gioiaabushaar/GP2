
import secrets
import uuid
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import or_, text
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.core.models import (
    User, Challenge, Writeup, Event, Submission, LabSession
)
from app.core.security import hash_password
from app.main import app



def cleanup(emails, challenge_title):
    """Remove only records created by this test."""
    with SessionLocal() as db:
        user_ids = [
            row[0]
            for row in db.query(User.id)
            .filter(User.email.in_(emails))
            .all()
        ]

        challenge = (
            db.query(Challenge)
            .filter(Challenge.title == challenge_title)
            .first()
        )

        challenge_id = challenge.id if challenge else None

        # Clean each table using only its own columns.
        for model in (Event, Submission, LabSession):
            conditions = []

            if user_ids:
                conditions.append(model.user_id.in_(user_ids))

            if challenge_id is not None:
                conditions.append(model.challenge_id == challenge_id)

            if conditions:
                db.query(model).filter(or_(*conditions)).delete(
                    synchronize_session=False
                )

        if challenge_id is not None:
            db.query(Writeup).filter(
                Writeup.challenge_id == challenge_id
            ).delete(synchronize_session=False)

            db.query(Challenge).filter(
                Challenge.id == challenge_id
            ).delete(synchronize_session=False)

        if user_ids:
            db.query(User).filter(
                User.id.in_(user_ids)
            ).delete(synchronize_session=False)

        db.commit()



def main():
    # Prevent accidental execution against SQLite or a remote database.
    if engine.dialect.name != "postgresql":
        raise RuntimeError("This test requires PostgreSQL.")

    if engine.url.host not in ("localhost", "127.0.0.1", "::1"):
        raise RuntimeError("This script is restricted to local PostgreSQL.")

    with engine.connect() as connection:
        database = connection.execute(
            text("SELECT current_database()")
        ).scalar_one()

    if database != "nexis_db":
        raise RuntimeError("Expected local nexis_db database.")

    if len(settings.nexis_secret_key.encode()) < 32:
        raise RuntimeError("JWT secret must be at least 32 bytes.")

    suffix = uuid.uuid4().hex[:10]

    student_email = f"test-student-{suffix}@example.com"
    instructor_email = f"test-instructor-{suffix}@example.com"
    challenge_title = f"PostgreSQL Integration Test {suffix}"

    student_password = secrets.token_urlsafe(20)
    instructor_password = secrets.token_urlsafe(20)

    emails = [student_email, instructor_email]

    print("Target: local PostgreSQL / nexis_db")

    try:
        with TestClient(app) as client:

            # 1. Student registration
            response = client.post(
                "/api/auth/register",
                json={
                    "email": student_email,
                    "full_name": "Integration Test Student",
                    "password": student_password,
                },
            )
            assert response.status_code == 201, response.text
            print("PASS: Student registration")

            # 2. Student login
            response = client.post(
                "/api/auth/login",
                json={
                    "email": student_email,
                    "password": student_password,
                },
            )
            assert response.status_code == 200, response.text

            student_token = response.json()["access_token"]
            student_headers = {
                "Authorization": f"Bearer {student_token}"
            }
            print("PASS: Student login")

            # 3. Current user
            response = client.get(
                "/api/auth/me",
                headers=student_headers,
            )
            assert response.status_code == 200, response.text
            assert response.json()["role"] == "student"
            print("PASS: Student profile and JWT")

            # 4. Student cannot access instructor analytics
            response = client.get(
                "/api/analytics/instructor/overview",
                headers=student_headers,
            )
            assert response.status_code == 403, response.text
            print("PASS: Student denied instructor analytics")

            # Student cannot create a challenge
            response = client.post(
                "/api/challenges",
                headers=student_headers,
                json={
                    "title": challenge_title,
                    "description": "Temporary integration test",
                    "category": "Web",
                    "difficulty": "Easy",
                    "points": 100,
                    "flag": "NEXIS{integration_test}",
                    "writeup": "Temporary test writeup",
                },
            )
            assert response.status_code == 403, response.text
            print("PASS: Student denied challenge creation")

            # 5. Create instructor directly as an operator would.
            with SessionLocal() as db:
                instructor = User(
                    email=instructor_email,
                    full_name="Integration Test Instructor",
                    password_hash=hash_password(instructor_password),
                    role="instructor",
                )
                db.add(instructor)
                db.commit()

            # 6. Instructor login
            response = client.post(
                "/api/auth/login",
                json={
                    "email": instructor_email,
                    "password": instructor_password,
                },
            )
            assert response.status_code == 200, response.text

            instructor_token = response.json()["access_token"]
            instructor_headers = {
                "Authorization": f"Bearer {instructor_token}"
            }
            assert response.json()["user"]["role"] == "instructor"
            print("PASS: Instructor creation and login")

            # Instructor profile
            response = client.get(
                "/api/auth/me",
                headers=instructor_headers,
            )
            assert response.status_code == 200, response.text
            assert response.json()["role"] == "instructor"
            print("PASS: Instructor profile")

            # 7. Instructor analytics access
            response = client.get(
                "/api/analytics/instructor/overview",
                headers=instructor_headers,
            )
            assert response.status_code == 200, response.text
            print("PASS: Instructor analytics access")

            # 8. Instructor can create a challenge
            response = client.post(
                "/api/challenges",
                headers=instructor_headers,
                json={
                    "title": challenge_title,
                    "description": "Temporary PostgreSQL integration test",
                    "category": "Web",
                    "difficulty": "Easy",
                    "points": 100,
                    "flag": "NEXIS{integration_test}",
                    "writeup": "Temporary test writeup",
                },
            )
            assert response.status_code == 201, response.text
            print("PASS: Instructor challenge creation")

        print("\nALL POSTGRESQL INTEGRATION TESTS PASSED")

    finally:
        cleanup(emails, challenge_title)
        print("Temporary test data cleaned up.")
        engine.dispose()


if __name__ == "__main__":
    main()
