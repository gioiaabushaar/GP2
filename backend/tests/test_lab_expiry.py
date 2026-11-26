"""The website reads each lab's expiry time from the server instead of keeping it in the browser."""
import os
import tempfile
from datetime import datetime, timedelta, timezone

os.environ["NEXIS_DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.gettempdir(), "nexis_pytest_lab_expiry.db").replace("\\", "/")
os.environ["NEXIS_SECRET_KEY"] = "pytest-only-secret-key-for-lab-expiry-tests"
os.environ["NEXIS_ALLOW_DOCKER"] = "false"

from fastapi.testclient import TestClient

from app.core.db import Base, SessionLocal, engine
from app.core.models import Challenge, LabSession, User
from app.core.security import hash_password
from app.main import app
from app.modules.labs import router as labs_router

PASSWORD = "SecurePassword123!"


def test_my_labs_include_when_each_lab_expires():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"email": "student@example.com", "full_name": "Student One", "password": PASSWORD})
        token = client.post("/api/auth/login", json={"email": "student@example.com", "password": PASSWORD}).json()["access_token"]
        started = datetime(2026, 11, 26, 9, 0, tzinfo=timezone.utc)
        with SessionLocal() as db:
            c = Challenge(title="Demo", description="Demo challenge.", category="Web", difficulty="Easy", points=100, flag_hash=hash_password("NEXIS{x}"))
            db.add(c)
            db.flush()
            user_id = db.query(User).filter_by(email="student@example.com").one().id
            db.add(LabSession(user_id=user_id, challenge_id=c.id, container_id="abc123", status="running", started_at=started))
            db.commit()
        lab = client.get("/api/labs/mine", headers={"Authorization": "Bearer " + token}).json()[0]
        expires = datetime.fromisoformat(lab["expires_at"])
        expires = expires if expires.tzinfo else expires.replace(tzinfo=timezone.utc)
        assert expires == started + timedelta(minutes=labs_router.LAB_TTL_MINUTES)
