"""Tests for courses and one-click deployment records (instructor pages)."""
import os
import tempfile

os.environ["NEXIS_DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.gettempdir(), "nexis_pytest_deployments.db").replace("\\", "/")
os.environ["NEXIS_SECRET_KEY"] = "pytest-only-secret-key-for-deployment-tests"
os.environ["NEXIS_ALLOW_DOCKER"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.core.db import Base, SessionLocal, engine
from app.core.models import Challenge, User
from app.core.security import hash_password
from app.main import app

PASSWORD = "SecurePassword123!"


def login(client, email):
    token = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": "Bearer " + token}


@pytest.fixture()
def env():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        with SessionLocal() as db:
            db.add(User(email="teacher@example.com", full_name="Dr. Teacher", password_hash=hash_password(PASSWORD), role="instructor"))
            db.add(Challenge(title="SQL Injection Basics", description="Demo challenge.", category="Web", difficulty="Easy", points=100, flag_hash=hash_password("NEXIS{x}")))
            db.commit()
            challenge_id = db.query(Challenge).one().id
        client.post("/api/auth/register", json={"email": "student@example.com", "full_name": "Student One", "password": PASSWORD})
        yield client, login(client, "teacher@example.com"), login(client, "student@example.com"), challenge_id


def courses(client, headers):
    return client.get("/api/courses", headers=headers).json()


# ---------- Courses ----------

def test_default_courses_are_in_the_database(env):
    client, teacher, _, _ = env
    assert [c["name"] for c in courses(client, teacher)] == [
        "Network Security Basics", "Web Application Security", "Cryptography Fundamentals", "Digital Forensics",
    ]


def test_instructor_adds_renames_and_deletes_a_course(env):
    client, teacher, _, _ = env
    new = client.post("/api/courses", headers=teacher, json={"name": "Ethical Hacking"})
    assert new.status_code == 201
    renamed = client.patch(f"/api/courses/{new.json()['id']}", headers=teacher, json={"name": "Ethical Hacking 2"})
    assert renamed.json()["name"] == "Ethical Hacking 2"
    assert client.delete(f"/api/courses/{new.json()['id']}", headers=teacher).status_code == 204
    assert "Ethical Hacking 2" not in [c["name"] for c in courses(client, teacher)]


def test_course_names_are_unique(env):
    client, teacher, _, _ = env
    assert client.post("/api/courses", headers=teacher, json={"name": "digital forensics"}).status_code == 409


def test_students_cannot_manage_courses(env):
    client, _, student, _ = env
    assert client.get("/api/courses", headers=student).status_code == 403
    assert client.post("/api/courses", headers=student, json={"name": "X course"}).status_code == 403


# ---------- Deployments ----------

def test_capacity_comes_from_the_server(env):
    client, teacher, _, _ = env
    cap = client.get("/api/deployments/capacity", headers=teacher).json()
    assert cap == {"host_ram_gb": 32, "reserved_gb": 4, "lab_memory_mb": 256, "max_labs": 112}


def test_deployment_within_capacity_is_recorded(env):
    client, teacher, _, challenge_id = env
    course = courses(client, teacher)[0]
    r = client.post("/api/deployments", headers=teacher, json={"course_id": course["id"], "challenge_id": challenge_id, "students": 30})
    assert r.status_code == 201 and r.json()["status"] == "running"
    history = client.get("/api/deployments", headers=teacher).json()
    assert history[0]["course_name"] == "Network Security Basics" and history[0]["challenge_title"] == "SQL Injection Basics"
    assert history[0]["students"] == 30


def test_deployment_over_capacity_is_refused_and_recorded(env):
    client, teacher, _, challenge_id = env
    course = courses(client, teacher)[0]
    r = client.post("/api/deployments", headers=teacher, json={"course_id": course["id"], "challenge_id": challenge_id, "students": 986})
    assert r.status_code == 201 and r.json()["status"] == "refused" and "112" in r.json()["reason"]
    assert client.get("/api/deployments", headers=teacher).json()[0]["status"] == "refused"


def test_history_keeps_the_course_name_used_at_the_time(env):
    client, teacher, _, challenge_id = env
    course = courses(client, teacher)[0]
    client.post("/api/deployments", headers=teacher, json={"course_id": course["id"], "challenge_id": challenge_id, "students": 5})
    client.patch(f"/api/courses/{course['id']}", headers=teacher, json={"name": "Renamed course"})
    assert client.get("/api/deployments", headers=teacher).json()[0]["course_name"] == "Network Security Basics"


def test_unknown_course_or_challenge_is_404(env):
    client, teacher, _, challenge_id = env
    course = courses(client, teacher)[0]
    assert client.post("/api/deployments", headers=teacher, json={"course_id": 999, "challenge_id": challenge_id, "students": 5}).status_code == 404
    assert client.post("/api/deployments", headers=teacher, json={"course_id": course["id"], "challenge_id": 999, "students": 5}).status_code == 404


def test_students_cannot_deploy_or_see_history(env):
    client, _, student, challenge_id = env
    assert client.post("/api/deployments", headers=student, json={"course_id": 1, "challenge_id": challenge_id, "students": 5}).status_code == 403
    assert client.get("/api/deployments", headers=student).status_code == 403
