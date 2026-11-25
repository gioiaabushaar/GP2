"""Tests for the Web Labs module: the PortSwigger lab library and the timed web lab exams."""
import os
import tempfile
from datetime import datetime, timedelta, timezone

# Separate database and test key, set before the application is imported.
os.environ["NEXIS_DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.gettempdir(), "nexis_pytest_web_labs.db").replace("\\", "/")
os.environ["NEXIS_SECRET_KEY"] = "pytest-only-secret-key-for-web-lab-tests"
os.environ["NEXIS_ALLOW_DOCKER"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import Base, SessionLocal, engine
from app.core.models import User
from app.core.security import hash_password
from app.main import app
from app.modules.web_labs import router as web_labs

PASSWORD = "SecurePassword123!"


def login(client, email):
    token = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": "Bearer " + token}


def register_student(client, email, name):
    client.post("/api/auth/register", json={"email": email, "full_name": name, "password": PASSWORD})
    return login(client, email)


@pytest.fixture()
def env():
    Base.metadata.drop_all(bind=engine)
    with TestClient(app) as client:
        with SessionLocal() as db:
            db.add(User(email="teacher@example.com", full_name="Dr. Teacher", password_hash=hash_password(PASSWORD), role="instructor"))
            db.commit()
        teacher = login(client, "teacher@example.com")
        student = register_student(client, "student@example.com", "Student One")
        yield client, teacher, student


@pytest.fixture()
def clock(monkeypatch):
    """Lets a test move the server's clock forward."""
    state = {"now": datetime.now(timezone.utc)}
    monkeypatch.setattr(web_labs, "utcnow", lambda: state["now"])

    def advance(**delta):
        state["now"] += timedelta(**delta)

    return advance


# ---------- Library ----------

def test_library_needs_login(env):
    client, _, _ = env
    assert client.get("/api/web-labs").status_code == 401


def test_library_lists_portswigger_labs_by_topic(env):
    client, _, student = env
    body = client.get("/api/web-labs", headers=student).json()
    assert body["total"] == sum(len(t["labs"]) for t in body["topics"]) > 0
    lab = body["topics"][0]["labs"][0]
    assert lab["url"].startswith("https://portswigger.net/web-security/") and lab["title"]


# ---------- Exams: listing and starting ----------

def test_students_see_exams_without_the_lab_pool(env):
    client, _, student = env
    quizzes = client.get("/api/web-labs/quizzes", headers=student).json()
    assert [q["title"] for q in quizzes] == ["Quiz 1", "Quiz 2", "Quiz 3"]
    assert all(q["duration_minutes"] == 7 and q["labs_per_attempt"] == 3 for q in quizzes)
    assert all("pool" not in q for q in quizzes)


def test_instructors_see_the_lab_pool(env):
    client, teacher, _ = env
    quizzes = client.get("/api/web-labs/quizzes", headers=teacher).json()
    assert all(len(q["pool"]) == q["pool_size"] >= 3 for q in quizzes)


def test_start_assigns_three_random_labs_from_the_quiz_pool(env):
    client, teacher, student = env
    pool = {lab["url"] for lab in client.get("/api/web-labs/quizzes", headers=teacher).json()[0]["pool"]}
    r = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student)
    assert r.status_code == 201
    attempt = r.json()
    urls = [lab["url"] for lab in attempt["labs"]]
    assert len(urls) == len(set(urls)) == 3 and set(urls) <= pool
    assert attempt["status"] == "active" and 415 <= attempt["seconds_left"] <= 420


def test_starting_again_returns_the_same_exam(env):
    client, _, student = env
    first = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student).json()
    again = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student)
    assert again.status_code == 200
    assert again.json()["id"] == first["id"] and again.json()["labs"] == first["labs"]


def test_only_one_open_exam_at_a_time(env):
    client, _, student = env
    client.post("/api/web-labs/quizzes/quiz-1/start", headers=student)
    assert client.post("/api/web-labs/quizzes/quiz-2/start", headers=student).status_code == 409


def _miss_first_open_check(monkeypatch):
    """Simulates two start requests at the same moment: the "is an exam open?" check misses the other one."""
    real = web_labs._open_attempt
    calls = {"n": 0}

    def stale(db, user_id):
        calls["n"] += 1
        return None if calls["n"] == 1 else real(db, user_id)

    monkeypatch.setattr(web_labs, "_open_attempt", stale)


def test_simultaneous_start_returns_the_existing_exam(env, monkeypatch):
    client, _, student = env
    first = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student).json()
    _miss_first_open_check(monkeypatch)
    again = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student)
    assert again.status_code == 200 and again.json()["id"] == first["id"]


def test_simultaneous_start_of_another_quiz_is_refused(env, monkeypatch):
    client, _, student = env
    client.post("/api/web-labs/quizzes/quiz-1/start", headers=student)
    _miss_first_open_check(monkeypatch)
    assert client.post("/api/web-labs/quizzes/quiz-2/start", headers=student).status_code == 409


def test_database_allows_only_one_open_exam_per_student(env):
    from sqlalchemy.exc import IntegrityError
    from app.modules.web_labs.models import WebLabAttempt

    client, _, student = env
    client.post("/api/web-labs/quizzes/quiz-1/start", headers=student)
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.email == "student@example.com"))
        db.add(WebLabAttempt(user_id=user_id, quiz_id="quiz-2", labs_json="[]", ends_at=datetime.now(timezone.utc)))
        with pytest.raises(IntegrityError):
            db.commit()


def test_unknown_quiz_is_404(env):
    client, _, student = env
    assert client.post("/api/web-labs/quizzes/quiz-9/start", headers=student).status_code == 404


def test_instructors_do_not_take_exams(env):
    client, teacher, _ = env
    assert client.post("/api/web-labs/quizzes/quiz-1/start", headers=teacher).status_code == 403


# ---------- During the exam ----------

def test_student_marks_and_unmarks_a_lab_as_solved(env):
    client, _, student = env
    attempt = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student).json()
    marked = client.post(f"/api/web-labs/attempts/{attempt['id']}/labs/1/solved", headers=student, json={"solved": True}).json()
    assert marked["solved_count"] == 1 and marked["labs"][1]["solved"] is True
    unmarked = client.post(f"/api/web-labs/attempts/{attempt['id']}/labs/1/solved", headers=student, json={"solved": False}).json()
    assert unmarked["solved_count"] == 0


def test_marking_a_lab_that_does_not_exist_is_404(env):
    client, _, student = env
    attempt = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student).json()
    assert client.post(f"/api/web-labs/attempts/{attempt['id']}/labs/3/solved", headers=student, json={"solved": True}).status_code == 404


def test_students_cannot_touch_another_students_exam(env):
    client, _, student = env
    other = register_student(client, "second@example.com", "Student Two")
    attempt = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student).json()
    assert client.post(f"/api/web-labs/attempts/{attempt['id']}/labs/0/solved", headers=other, json={"solved": True}).status_code == 404


def test_current_exam_survives_a_page_refresh(env):
    client, _, student = env
    attempt = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student).json()
    assert client.get("/api/web-labs/attempts/current", headers=student).json()["id"] == attempt["id"]


# ---------- Time over, finishing and the lock ----------

def test_exam_locks_when_time_is_over(env, clock):
    client, _, student = env
    attempt = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student).json()
    clock(minutes=7, seconds=1)
    current = client.get("/api/web-labs/attempts/current", headers=student).json()
    assert current["status"] == "locked" and current["seconds_left"] == 0
    assert client.post(f"/api/web-labs/attempts/{attempt['id']}/labs/0/solved", headers=student, json={"solved": True}).status_code == 409


def test_locked_exam_blocks_starting_any_exam(env, clock):
    client, _, student = env
    client.post("/api/web-labs/quizzes/quiz-1/start", headers=student)
    clock(minutes=8)
    assert client.post("/api/web-labs/quizzes/quiz-2/start", headers=student).status_code == 409
    again = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student)
    assert again.status_code == 200 and again.json()["status"] == "locked"


def test_finishing_early_locks_the_exam(env):
    client, _, student = env
    attempt = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student).json()
    finished = client.post(f"/api/web-labs/attempts/{attempt['id']}/finish", headers=student).json()
    assert finished["status"] == "locked" and finished["seconds_left"] == 0


# ---------- Instructor view and unlock ----------

def test_instructor_sees_every_attempt_with_the_student_name(env):
    client, teacher, student = env
    attempt = client.post("/api/web-labs/quizzes/quiz-2/start", headers=student).json()
    client.post(f"/api/web-labs/attempts/{attempt['id']}/labs/0/solved", headers=student, json={"solved": True})
    rows = client.get("/api/web-labs/attempts", headers=teacher).json()
    assert len(rows) == 1
    assert rows[0]["student"]["full_name"] == "Student One" and rows[0]["quiz_title"] == "Quiz 2" and rows[0]["solved_count"] == 1


def test_students_cannot_list_all_attempts(env):
    client, _, student = env
    assert client.get("/api/web-labs/attempts", headers=student).status_code == 403


def test_instructor_unlock_lets_the_student_start_again(env, clock):
    client, teacher, student = env
    first = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student).json()
    clock(minutes=8)
    reset = client.post(f"/api/web-labs/attempts/{first['id']}/reset", headers=teacher).json()
    assert reset["status"] == "reset"
    assert client.get("/api/web-labs/attempts/current", headers=student).json() is None
    second = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student)
    assert second.status_code == 201 and second.json()["id"] != first["id"]


def test_students_cannot_unlock(env):
    client, _, student = env
    attempt = client.post("/api/web-labs/quizzes/quiz-1/start", headers=student).json()
    assert client.post(f"/api/web-labs/attempts/{attempt['id']}/reset", headers=student).status_code == 403
