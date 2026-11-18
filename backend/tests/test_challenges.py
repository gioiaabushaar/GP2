"""Tests for Sura's module: creating challenges, checking flags and awarding points."""
import os
import tempfile

# Separate database and test key, set before the application is imported.
os.environ["NEXIS_DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.gettempdir(), "nexis_pytest_challenges.db").replace("\\", "/")
os.environ["NEXIS_SECRET_KEY"] = "pytest-only-secret-key-for-challenge-tests"
os.environ["NEXIS_ALLOW_DOCKER"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func

from app.core.db import Base, SessionLocal, engine
from app.core.models import Challenge, Submission, User
from app.core.security import hash_password
from app.main import app

PASSWORD = "SecurePassword123!"


def login(client, email):
    token = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return {"Authorization": "Bearer " + token}


def register_student(client, email, name):
    client.post("/api/auth/register", json={"email": email, "full_name": name, "password": PASSWORD})
    return login(client, email)


def new_challenge(**overrides):
    body = {
        "title": "Caesar Cipher Breaker",
        "description": "Recover the hidden message from a shifted alphabet.",
        "category": "Cryptography",
        "difficulty": "Easy",
        "points": 150,
        "flag": "NEXIS{caesar_shift_3}",
        "writeup": "A Caesar cipher shifts every letter by a fixed amount; try all 25 shifts.",
    }
    body.update(overrides)
    return body


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


# ---------- Creating challenges (instructor) ----------

def test_instructor_creates_challenge_without_exposing_flag(env):
    client, teacher, _ = env
    r = client.post("/api/challenges", headers=teacher, json=new_challenge())
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Caesar Cipher Breaker" and body["points"] == 150
    assert "flag" not in body and "flag_hash" not in body


def test_flag_is_stored_hashed_not_as_plain_text(env):
    client, teacher, _ = env
    cid = client.post("/api/challenges", headers=teacher, json=new_challenge()).json()["id"]
    with SessionLocal() as db:
        stored = db.get(Challenge, cid).flag_hash
    assert stored != "NEXIS{caesar_shift_3}" and "caesar_shift_3" not in stored


def test_points_default_from_difficulty_when_not_given(env):
    client, teacher, _ = env
    body = new_challenge(difficulty="Medium")
    del body["points"]
    assert client.post("/api/challenges", headers=teacher, json=body).json()["points"] == 200


def test_flag_must_use_nexis_format(env):
    client, teacher, _ = env
    assert client.post("/api/challenges", headers=teacher, json=new_challenge(flag="caesar_shift_3")).status_code == 422


def test_unknown_category_is_rejected(env):
    client, teacher, _ = env
    assert client.post("/api/challenges", headers=teacher, json=new_challenge(category="Cooking")).status_code == 422


def test_duplicate_title_is_rejected(env):
    client, teacher, _ = env
    assert client.post("/api/challenges", headers=teacher, json=new_challenge()).status_code == 201
    assert client.post("/api/challenges", headers=teacher, json=new_challenge(title="caesar cipher breaker")).status_code == 409


def test_student_cannot_create_challenge(env):
    client, _, student = env
    assert client.post("/api/challenges", headers=student, json=new_challenge()).status_code == 403


# ---------- Browsing and filtering ----------

def test_list_filters_by_category_and_difficulty(env):
    client, teacher, student = env
    client.post("/api/challenges", headers=teacher, json=new_challenge())
    client.post("/api/challenges", headers=teacher, json=new_challenge(title="Hidden File Forensics", category="Forensics", difficulty="Hard", flag="NEXIS{hidden_file}"))
    assert [c["title"] for c in client.get("/api/challenges?category=Forensics", headers=student).json()] == ["Hidden File Forensics"]
    assert [c["title"] for c in client.get("/api/challenges?difficulty=Easy", headers=student).json()] == ["Caesar Cipher Breaker"]


# ---------- Submitting flags and earning points (student) ----------

def test_wrong_flag_gives_no_points_and_counts_attempt(env):
    client, teacher, student = env
    cid = client.post("/api/challenges", headers=teacher, json=new_challenge()).json()["id"]
    r = client.post(f"/api/challenges/{cid}/submit", headers=student, json={"flag": "NEXIS{wrong}"}).json()
    assert r["correct"] is False and r["points_awarded"] == 0 and r["total_score"] == 0
    assert r["attempt_number"] == 1


def test_flag_check_is_case_sensitive(env):
    client, teacher, student = env
    cid = client.post("/api/challenges", headers=teacher, json=new_challenge()).json()["id"]
    assert client.post(f"/api/challenges/{cid}/submit", headers=student, json={"flag": "nexis{caesar_shift_3}"}).json()["correct"] is False


def test_correct_flag_awards_challenge_points(env):
    client, teacher, student = env
    cid = client.post("/api/challenges", headers=teacher, json=new_challenge()).json()["id"]
    client.post(f"/api/challenges/{cid}/submit", headers=student, json={"flag": "NEXIS{wrong}"})
    r = client.post(f"/api/challenges/{cid}/submit", headers=student, json={"flag": "NEXIS{caesar_shift_3}"}).json()
    assert r["correct"] is True and r["points_awarded"] == 150 and r["total_score"] == 150
    assert r["attempt_number"] == 2


def test_spaces_around_pasted_flag_are_ignored(env):
    client, teacher, student = env
    cid = client.post("/api/challenges", headers=teacher, json=new_challenge()).json()["id"]
    assert client.post(f"/api/challenges/{cid}/submit", headers=student, json={"flag": "  NEXIS{caesar_shift_3}\n"}).json()["correct"] is True


def test_solving_again_gives_no_extra_points(env):
    client, teacher, student = env
    cid = client.post("/api/challenges", headers=teacher, json=new_challenge()).json()["id"]
    client.post(f"/api/challenges/{cid}/submit", headers=student, json={"flag": "NEXIS{caesar_shift_3}"})
    r = client.post(f"/api/challenges/{cid}/submit", headers=student, json={"flag": "NEXIS{caesar_shift_3}"}).json()
    assert r["already_solved"] is True and r["points_awarded"] == 0 and r["total_score"] == 150
    with SessionLocal() as db:
        assert db.scalar(select(func.count(Submission.id))) == 1  # the repeat is not stored as a new attempt


def test_my_score_adds_up_solved_challenges(env):
    client, teacher, student = env
    a = client.post("/api/challenges", headers=teacher, json=new_challenge()).json()["id"]
    b = client.post("/api/challenges", headers=teacher, json=new_challenge(title="Hidden File Forensics", category="Forensics", points=300, flag="NEXIS{hidden_file}")).json()["id"]
    client.post(f"/api/challenges/{a}/submit", headers=student, json={"flag": "NEXIS{caesar_shift_3}"})
    client.post(f"/api/challenges/{b}/submit", headers=student, json={"flag": "NEXIS{hidden_file}"})
    r = client.get("/api/challenges/my-score", headers=student).json()
    assert r["total_score"] == 450 and r["solved_count"] == 2
    assert {s["title"] for s in r["solved"]} == {"Caesar Cipher Breaker", "Hidden File Forensics"}


def test_list_marks_which_challenges_the_student_solved(env):
    client, teacher, student = env
    a = client.post("/api/challenges", headers=teacher, json=new_challenge()).json()["id"]
    client.post("/api/challenges", headers=teacher, json=new_challenge(title="Hidden File Forensics", category="Forensics", flag="NEXIS{hidden_file}"))
    client.post(f"/api/challenges/{a}/submit", headers=student, json={"flag": "NEXIS{caesar_shift_3}"})
    solved = {c["title"]: c["solved"] for c in client.get("/api/challenges", headers=student).json()}
    assert solved == {"Caesar Cipher Breaker": True, "Hidden File Forensics": False}


# ---------- Leaderboard (instructor) ----------

def test_leaderboard_ranks_students_by_score(env):
    client, teacher, student = env
    other = register_student(client, "second@example.com", "Student Two")
    a = client.post("/api/challenges", headers=teacher, json=new_challenge()).json()["id"]
    b = client.post("/api/challenges", headers=teacher, json=new_challenge(title="Hidden File Forensics", category="Forensics", points=300, flag="NEXIS{hidden_file}")).json()["id"]
    client.post(f"/api/challenges/{a}/submit", headers=student, json={"flag": "NEXIS{caesar_shift_3}"})
    client.post(f"/api/challenges/{b}/submit", headers=other, json={"flag": "NEXIS{hidden_file}"})
    board = client.get("/api/challenges/leaderboard", headers=teacher).json()
    assert [(row["rank"], row["full_name"], row["total_score"]) for row in board] == [(1, "Student Two", 300), (2, "Student One", 150)]


def test_students_cannot_see_leaderboard(env):
    client, _, student = env
    assert client.get("/api/challenges/leaderboard", headers=student).status_code == 403
