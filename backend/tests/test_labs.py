import os
import tempfile

# Separate database and test key, set before the application is imported.
os.environ["NEXIS_DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.gettempdir(), "nexis_pytest_labs.db").replace("\\", "/")
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


class FakeContainer:
    def __init__(self, client, cid):
        self.client, self.id = client, cid
        self.labels = {"nexis.managed": "true"}

    def remove(self, force=False):
        if self.client.fail_remove:
            raise RuntimeError("docker error")
        self.client.alive.pop(self.id, None)


class FakeDocker:
    """Stands in for the Docker client so these tests run without Docker."""

    def __init__(self):
        self.alive, self.n, self.fail_remove = {}, 0, False
        self.containers = self

    def run(self, image, **kwargs):
        self.n += 1
        c = FakeContainer(self, f"fake{self.n:060d}")
        self.alive[c.id] = c
        return c

    def get(self, cid):
        if cid not in self.alive:
            raise NotFound("gone")
        return self.alive[cid]


@pytest.fixture()
def env(monkeypatch):
    fake = FakeDocker()
    monkeypatch.setattr(labs_router, "client_or_503", lambda: fake)
    monkeypatch.setattr(settings, "nexis_allow_docker", True)
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        client.post("/api/auth/register", json={"email": "s@example.com", "full_name": "Student One", "password": "SecurePassword123!"})
        token = client.post("/api/auth/login", json={"email": "s@example.com", "password": "SecurePassword123!"}).json()["access_token"]
        with SessionLocal() as db:
            for title in ("Lab A", "Lab B"):
                db.add(Challenge(title=title, description="Test lab description", category="Web", difficulty="Easy",
                                 points=100, flag_hash="x", image_name="nexis-demo-lab:latest"))
            db.commit()
        yield client, {"Authorization": "Bearer " + token}, fake


def test_start_reports_provision_time_and_expiry(env):
    client, h, fake = env
    r = client.post("/api/labs/start/1", headers=h)
    assert r.status_code == 201
    assert r.json()["provision_seconds"] >= 0 and r.json()["expires_in_minutes"] == labs_router.LAB_TTL_MINUTES
    assert len(fake.alive) == 1


def test_one_active_lab_per_student_even_across_challenges(env):
    client, h, fake = env
    assert client.post("/api/labs/start/1", headers=h).status_code == 201
    assert client.post("/api/labs/start/2", headers=h).status_code == 409
    assert len(fake.alive) == 1


def test_stop_removes_container(env):
    client, h, fake = env
    sid = client.post("/api/labs/start/1", headers=h).json()["session_id"]
    assert client.delete(f"/api/labs/{sid}", headers=h).json() == {"status": "stopped"}
    assert fake.alive == {}
    assert client.post("/api/labs/start/2", headers=h).status_code == 201  # can start another after stopping


def test_failed_stop_keeps_session_running(env):
    client, h, fake = env
    sid = client.post("/api/labs/start/1", headers=h).json()["session_id"]
    fake.fail_remove = True
    assert client.delete(f"/api/labs/{sid}", headers=h).status_code == 503
    assert client.get("/api/labs/mine", headers=h).json()[0]["status"] == "running"
    fake.fail_remove = False
    assert client.delete(f"/api/labs/{sid}", headers=h).json() == {"status": "stopped"}


def test_stop_when_container_already_gone(env):
    client, h, fake = env
    sid = client.post("/api/labs/start/1", headers=h).json()["session_id"]
    fake.alive.clear()
    assert client.delete(f"/api/labs/{sid}", headers=h).json() == {"status": "stopped"}


def test_expired_lab_is_removed_automatically(env):
    client, h, fake = env
    sid = client.post("/api/labs/start/1", headers=h).json()["session_id"]
    with SessionLocal() as db:
        s = db.get(LabSession, sid)
        s.started_at = s.started_at - timedelta(minutes=labs_router.LAB_TTL_MINUTES + 1)
        db.commit()
    mine = client.get("/api/labs/mine", headers=h).json()
    assert mine[0]["status"] == "expired"
    assert fake.alive == {}


def _login(client, email):
    client.post("/api/auth/register", json={"email": email, "full_name": "Other Student", "password": "SecurePassword123!"})
    token = client.post("/api/auth/login", json={"email": email, "password": "SecurePassword123!"}).json()["access_token"]
    return {"Authorization": "Bearer " + token}


def test_other_student_cannot_stop_my_lab(env):
    client, h, fake = env
    sid = client.post("/api/labs/start/1", headers=h).json()["session_id"]
    other = _login(client, "other@example.com")
    assert client.delete(f"/api/labs/{sid}", headers=other).status_code == 404
    assert len(fake.alive) == 1  # container still running


def test_unapproved_image_is_rejected(env):
    client, h, fake = env
    with SessionLocal() as db:
        c = db.get(Challenge, 1)
        c.image_name = "evil:latest"
        db.commit()
    assert client.post("/api/labs/start/1", headers=h).status_code == 400
    assert fake.alive == {}
