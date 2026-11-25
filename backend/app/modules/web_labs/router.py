"""Web Labs: the PortSwigger Web Security Academy library and timed web lab exams.

The labs themselves run on PortSwigger's servers; NEXIS lists them and links to them.
The exams follow the course instructor's quiz: 3 random labs from the quiz's pool and a
7-minute timer kept on the server, so refreshing the page cannot reset it. When the time
is over the exam locks until an instructor unlocks it.
"""
import json
import random
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.models import Event, User
from app.core.security import current_user, instructor
from app.modules.web_labs.models import WebLabAttempt

router = APIRouter(tags=["Web Labs | PortSwigger library & exams"])
DATA = Path(__file__).parent / "data"


def utcnow() -> datetime:
    """The server clock. Tests replace it to move time forward."""
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    # SQLite returns naive datetimes; NEXIS stores every time in UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@lru_cache
def _library() -> dict:
    return json.loads((DATA / "portswigger_labs.json").read_text(encoding="utf-8"))


@lru_cache
def _exams() -> dict:
    return json.loads((DATA / "quizzes.json").read_text(encoding="utf-8"))


def _find_quiz(quiz_id: str) -> dict | None:
    return next((q for q in _exams()["quizzes"] if q["id"] == quiz_id), None)


def _status(a: WebLabAttempt, now: datetime) -> str:
    if a.reset_at:
        return "reset"
    return "locked" if now >= _aware(a.ends_at) else "active"


def _view(a: WebLabAttempt, now: datetime, student: User | None = None) -> dict:
    labs = json.loads(a.labs_json)
    solved = set(json.loads(a.solved_json))
    status = _status(a, now)
    quiz = _find_quiz(a.quiz_id)
    data = {
        "id": a.id,
        "quiz_id": a.quiz_id,
        "quiz_title": quiz["title"] if quiz else a.quiz_id,
        "status": status,
        "started_at": _aware(a.started_at).isoformat(),
        "ends_at": _aware(a.ends_at).isoformat(),
        "seconds_left": max(0, int((_aware(a.ends_at) - now).total_seconds())) if status == "active" else 0,
        "labs": [{"index": i, "title": lab["title"], "url": lab["url"], "solved": i in solved} for i, lab in enumerate(labs)],
        "solved_count": len(solved),
        "reset_at": _aware(a.reset_at).isoformat() if a.reset_at else None,
    }
    if student:
        data["student"] = {"id": student.id, "full_name": student.full_name, "email": student.email}
    return data


def _open_attempt(db: Session, user_id: int) -> WebLabAttempt | None:
    """The student's exam that is still running or locked (not yet unlocked by an instructor)."""
    q = select(WebLabAttempt).where(WebLabAttempt.user_id == user_id, WebLabAttempt.reset_at.is_(None))
    return db.scalar(q.order_by(WebLabAttempt.id.desc()))


def _own_attempt(db: Session, attempt_id: int, user: User) -> WebLabAttempt:
    a = db.get(WebLabAttempt, attempt_id)
    if not a or a.user_id != user.id:
        raise HTTPException(404, "Exam not found")
    return a


# ---------- Library ----------

@router.get("")
def library(user: User = Depends(current_user)):
    data = _library()
    topics: dict[str, list[dict]] = {}
    for lab in data["labs"]:
        topics.setdefault(lab["topic"], []).append({"title": lab["title"], "url": lab["url"]})
    return {
        "source": data["source"],
        "total": len(data["labs"]),
        "topics": [{"name": name, "labs": labs} for name, labs in topics.items()],
    }


# ---------- Exams ----------

@router.get("/quizzes")
def list_exams(user: User = Depends(current_user)):
    out = []
    for q in _exams()["quizzes"]:
        item = {k: q[k] for k in ("id", "title", "description", "duration_minutes", "labs_per_attempt")}
        item["pool_size"] = len(q["pool"])
        item["rules"] = _exams()["rules"]
        if user.role == "instructor":
            item["pool"] = q["pool"]
        out.append(item)
    return out


@router.post("/quizzes/{quiz_id}/start", status_code=201)
def start_exam(quiz_id: str, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    quiz = _find_quiz(quiz_id)
    if not quiz:
        raise HTTPException(404, "Exam not found")
    if user.role != "student":
        raise HTTPException(403, "Exams are taken from student accounts")
    now = utcnow()
    current = _open_attempt(db, user.id)
    if current:
        return _existing_exam(current, quiz_id, response, now)

    labs = random.sample(quiz["pool"], quiz["labs_per_attempt"])
    a = WebLabAttempt(
        user_id=user.id, quiz_id=quiz_id, labs_json=json.dumps(labs), solved_json="[]",
        started_at=now, ends_at=now + timedelta(minutes=quiz["duration_minutes"]),
    )
    db.add(a)
    db.add(Event(user_id=user.id, kind="web_exam_started"))
    try:
        db.commit()
    except IntegrityError:
        # Another start request for this student won the race; answer with the exam it created.
        db.rollback()
        return _existing_exam(_open_attempt(db, user.id), quiz_id, response, now)
    db.refresh(a)
    return _view(a, now)


def _existing_exam(current: WebLabAttempt, quiz_id: str, response: Response, now: datetime) -> dict:
    """The student already has an open exam: return it if it is this quiz, otherwise refuse."""
    if current.quiz_id == quiz_id:
        response.status_code = 200  # same exam: a refresh or a second click returns it unchanged
        return _view(current, now)
    title = _find_quiz(current.quiz_id)["title"] if _find_quiz(current.quiz_id) else current.quiz_id
    if _status(current, now) == "locked":
        raise HTTPException(409, f"Your {title} exam is locked. Ask the instructor to unlock it before starting another exam.")
    raise HTTPException(409, f"You already have {title} open. Finish it before starting another exam.")


@router.get("/attempts/current")
def current_exam(db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = _open_attempt(db, user.id)
    return _view(a, utcnow()) if a else None


class SolvedMark(BaseModel):
    solved: bool


@router.post("/attempts/{attempt_id}/labs/{index}/solved")
def mark_solved(attempt_id: int, index: int, data: SolvedMark, db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = _own_attempt(db, attempt_id, user)
    now = utcnow()
    if _status(a, now) != "active":
        raise HTTPException(409, "This exam is over. Lab marks can no longer change.")
    if not 0 <= index < len(json.loads(a.labs_json)):
        raise HTTPException(404, "Lab not found in this exam")
    solved = set(json.loads(a.solved_json))
    if data.solved:
        solved.add(index)
    else:
        solved.discard(index)
    a.solved_json = json.dumps(sorted(solved))
    db.add(Event(user_id=user.id, kind="web_lab_marked_solved" if data.solved else "web_lab_unmarked"))
    db.commit()
    return _view(a, now)


@router.post("/attempts/{attempt_id}/finish")
def finish_exam(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = _own_attempt(db, attempt_id, user)
    now = utcnow()
    if _status(a, now) == "active":
        a.ends_at = now
        db.add(Event(user_id=user.id, kind="web_exam_finished"))
        db.commit()
    return _view(a, now)


# ---------- Instructor ----------

@router.get("/attempts")
def all_attempts(quiz_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(instructor)):
    q = select(WebLabAttempt, User).join(User, User.id == WebLabAttempt.user_id)
    if quiz_id:
        q = q.where(WebLabAttempt.quiz_id == quiz_id)
    now = utcnow()
    return [_view(a, now, student) for a, student in db.execute(q.order_by(WebLabAttempt.id.desc()).limit(500)).all()]


@router.post("/attempts/{attempt_id}/reset")
def unlock_exam(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(instructor)):
    a = db.get(WebLabAttempt, attempt_id)
    if not a:
        raise HTTPException(404, "Exam not found")
    now = utcnow()
    if not a.reset_at:
        a.reset_at, a.reset_by = now, user.id
        db.add(Event(user_id=a.user_id, kind="web_exam_unlocked"))
        db.commit()
    return _view(a, now, db.get(User, a.user_id))
