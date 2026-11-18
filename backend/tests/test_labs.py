
import os
import tempfile

# Separate database and test key.
# These settings must be set before importing the application.
os.environ["NEXIS_DATABASE_URL"] = (
    "sqlite:///"
    + os.path.join(
        tempfile.gettempdir(),
        "nexis_pytest_labs.db"
    ).replace("\\", "/")
)
os.environ["NEXIS_SECRET_KEY"] = "pytest-only-secret-key-for-lab-tests"
os.environ["NEXIS_ALLOW_DOCKER"] = "false"

from datetime import timedelta

import pytest
from docker.errors import NotFound
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.db import Base, SessionLocal, engine
from app.core.models import Challenge, LabSession
from app.main import app
from app.modules.labs import router as labs_router


# ============================================================
# Fake Docker Container
# ============================================================

class FakeContainer:
    def __init__(self, client, cid):
        self.client, self.id = client, cid
        self.labels = {"nexis.managed": "true"}

    def remove(self, force=False):
        if self.client.fail_remove:
            raise RuntimeError("docker error")

        self.client.alive.pop(self.id, None)


# ============================================================
# Fake Docker Client
# ============================================================

class FakeDocker:
    """
    Stands in for the Docker client so these tests
    run without requiring a real Docker Engine.
    """

    def __init__(self):
        self.alive = {}
        self.n = 0
        self.fail_remove = False
        self.containers = self

    def run(self, image, **kwargs):
        self.n += 1

        container = FakeContainer(
            self,
            f"fake{self.n:060d}"
        )

        self.alive[container.id] = container
        return container

    def get(self, cid):
        if cid not in self.alive:
            raise NotFound("gone")

        return self.alive[cid]


# ============================================================
# Test Environment
# ============================================================

@pytest.fixture()
def env(monkeypatch):
    fake = FakeDocker()

    monkeypatch.setattr(
        labs_router,
        "client_or_503",
        lambda: fake
    )

    monkeypatch.setattr(
        settings,
        "nexis_allow_docker",
        True
    )

    Base.metadata.drop_all(bind=engine)

    with TestClient(app) as client:

        # Register a test student.
        client.post(
            "/api/auth/register",
            json={
                "email": "s@example.com",
                "full_name": "Student One",
                "password": "SecurePassword123!"
            }
        )

        # Log in and retrieve the access token.
        token = client.post(
            "/api/auth/login",
            json={
                "email": "s@example.com",
                "password": "SecurePassword123!"
            }
        ).json()["access_token"]

        # Create approved lab challenges.
        with SessionLocal() as db:
            for title in ("Lab A", "Lab B"):
                db.add(
                    Challenge(
                        title=title,
                        description="Test lab description",
                        category="Web",
                        difficulty="Easy",
                        points=100,
                        flag_hash="x",
                        image_name="nexis-demo-lab:latest"
                    )
                )

            db.commit()

        headers = {
            "Authorization": "Bearer " + token
        }

        yield client, headers, fake


# ============================================================
# Test 1: Provision Time and Expiration
# FR1
# ============================================================

def test_start_reports_provision_time_and_expiry(env):
    client, h, fake = env

    response = client.post(
        "/api/labs/start/1",
        headers=h
    )

    assert response.status_code == 201

    data = response.json()

    assert data["provision_seconds"] >= 0
    assert (
        data["expires_in_minutes"]
        == labs_router.LAB_TTL_MINUTES
    )

    assert len(fake.alive) == 1


# ============================================================
# Test 2: One Active Lab Per Student
# ============================================================

def test_one_active_lab_per_student_even_across_challenges(env):
    client, h, fake = env

    assert client.post(
        "/api/labs/start/1",
        headers=h
    ).status_code == 201

    assert client.post(
        "/api/labs/start/2",
        headers=h
    ).status_code == 409

    assert len(fake.alive) == 1


# ============================================================
# Test 3: Stop Removes Container
# FR2
# ============================================================

def test_stop_removes_container(env):
    client, h, fake = env

    sid = client.post(
        "/api/labs/start/1",
        headers=h
    ).json()["session_id"]

    response = client.delete(
        f"/api/labs/{sid}",
        headers=h
    )

    assert response.json() == {"status": "stopped"}
    assert fake.alive == {}

    # Student can start another lab after stopping.
    assert client.post(
        "/api/labs/start/2",
        headers=h
    ).status_code == 201


# ============================================================
# Test 4: Failed Stop Preserves Session
# ============================================================

def test_failed_stop_keeps_session_running(env):
    client, h, fake = env

    sid = client.post(
        "/api/labs/start/1",
        headers=h
    ).json()["session_id"]

    fake.fail_remove = True

    assert client.delete(
        f"/api/labs/{sid}",
        headers=h
    ).status_code == 503

    response = client.get(
        "/api/labs/mine",
        headers=h
    )

    assert response.json()[0]["status"] == "running"

    fake.fail_remove = False

    assert client.delete(
        f"/api/labs/{sid}",
        headers=h
    ).json() == {"status": "stopped"}


# ============================================================
# Test 5: Container Already Removed
# ============================================================

def test_stop_when_container_already_gone(env):
    client, h, fake = env

    sid = client.post(
        "/api/labs/start/1",
        headers=h
    ).json()["session_id"]

    fake.alive.clear()

    response = client.delete(
        f"/api/labs/{sid}",
        headers=h
    )

    assert response.json() == {"status": "stopped"}


# ============================================================
# Test 6: Automatic Expiration via API
# FR2
# ============================================================

def test_expired_lab_is_removed_automatically(env):
    client, h, fake = env

    sid = client.post(
        "/api/labs/start/1",
        headers=h
    ).json()["session_id"]

    # Simulate the expiration of the lab session.
    with SessionLocal() as db:
        session = db.get(LabSession, sid)

        session.started_at -= timedelta(
            minutes=labs_router.LAB_TTL_MINUTES + 1
        )

        db.commit()

    # API request triggers expired-lab cleanup.
    response = client.get(
        "/api/labs/mine",
        headers=h
    )

    assert response.json()[0]["status"] == "expired"
    assert fake.alive == {}


# ============================================================
# Helper: Login Another Student
# ============================================================

def _login(client, email):
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "full_name": "Other Student",
            "password": "SecurePassword123!"
        }
    )

    token = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": "SecurePassword123!"
        }
    ).json()["access_token"]

    return {
        "Authorization": "Bearer " + token
    }


# ============================================================
# Test 7: Student Ownership Protection
# ============================================================

def test_other_student_cannot_stop_my_lab(env):
    client, h, fake = env

    sid = client.post(
        "/api/labs/start/1",
        headers=h
    ).json()["session_id"]

    other = _login(
        client,
        "other@example.com"
    )

    response = client.delete(
        f"/api/labs/{sid}",
        headers=other
    )

    assert response.status_code == 404

    # Original student's container must remain running.
    assert len(fake.alive) == 1


# ============================================================
# Test 8: Reject Unapproved Docker Images
# ============================================================

def test_unapproved_image_is_rejected(env):
    client, h, fake = env

    with SessionLocal() as db:
        challenge = db.get(Challenge, 1)

        challenge.image_name = "evil:latest"

        db.commit()

    response = client.post(
        "/api/labs/start/1",
        headers=h
    )

    assert response.status_code == 400
    assert fake.alive == {}


# ============================================================
# Test 9: Background Reaper Removes Expired Labs
# FR2 - Background Cleanup
# ============================================================

def test_background_reaper_removes_expired_lab(env):
    client, h, fake = env

    # Step 1: Start an approved Docker lab.
    response = client.post(
        "/api/labs/start/1",
        headers=h
    )

    assert response.status_code == 201

    sid = response.json()["session_id"]

    # Verify that a container was created.
    assert len(fake.alive) == 1

    # Step 2: Simulate an expired lab.
    with SessionLocal() as db:
        session = db.get(LabSession, sid)

        session.started_at -= timedelta(
            minutes=labs_router.LAB_TTL_MINUTES + 1
        )

        db.commit()

    # Step 3: Execute one background cleanup pass.
    # No API request is made to trigger the cleanup.
    removed_count = labs_router._reap_once()

    assert removed_count == 1

    # Step 4: Verify Docker container removal.
    assert fake.alive == {}

    # Step 5: Verify database status.
    with SessionLocal() as db:
        session = db.get(LabSession, sid)

        assert session.status == "expired"
