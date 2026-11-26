"""Web Labs: the practice library and timed web lab exams, all stored in the database.

The labs themselves run on their own sites (PortSwigger by default); NEXIS lists them and links to
them. An exam draws N random labs from its pool and keeps the end time on the server, so refreshing
the page cannot reset it. When the time is over the exam locks until an instructor unlocks it.
Instructors manage exams, pools and the library from the website.
"""
import json
import random
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.models import Event, User
from app.core.security import current_user, instructor
from app.modules.web_labs.models import WebExam, WebExamLab, WebLabAttempt, WebLibraryLab

router = APIRouter(tags=["Web Labs | library & exams"])

LIBRARY_NOTE = "Labs open on their own site. PortSwigger labs need a free PortSwigger account."
URL_PATTERN = r"^https?://[^\s<>\"']+$"


def utcnow() -> datetime:
    """The server clock. Tests replace it to move time forward."""
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    # SQLite returns naive datetimes; NEXIS stores every time in UTC.
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------- Request bodies ----------

class LabIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(max_length=500, pattern=URL_PATTERN)


class LibraryLabIn(LabIn):
    topic: str = Field(min_length=1, max_length=120)


class LibraryLabUpdate(BaseModel):
    topic: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    url: str | None = Field(default=None, max_length=500, pattern=URL_PATTERN)


class ExamIn(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(default="", max_length=2000)
    duration_minutes: int = Field(ge=1, le=240)
    labs_per_attempt: int = Field(ge=1, le=20)
    rules: str = Field(default="", max_length=4000, description="One rule per line.")
    active: bool = True


class ExamUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    duration_minutes: int | None = Field(default=None, ge=1, le=240)
    labs_per_attempt: int | None = Field(default=None, ge=1, le=20)
    rules: str | None = Field(default=None, max_length=4000)
    active: bool | None = None


class SolvedMark(BaseModel):
    solved: bool


# ---------- Helpers ----------

def _pool(db: Session, exam_id: str) -> list[WebExamLab]:
    q = select(WebExamLab).where(WebExamLab.exam_id == exam_id).order_by(WebExamLab.position, WebExamLab.id)
    return list(db.scalars(q).all())


def _exam_view(db: Session, exam: WebExam, with_pool: bool) -> dict:
    pool = _pool(db, exam.id)
    data = {
        "id": exam.id, "title": exam.title, "description": exam.description,
        "duration_minutes": exam.duration_minutes, "labs_per_attempt": exam.labs_per_attempt,
        "rules": [r.strip() for r in exam.rules.splitlines() if r.strip()],
        "active": exam.active, "pool_size": len(pool),
    }
    if with_pool:
        data["pool"] = [{"id": lab.id, "title": lab.title, "url": lab.url} for lab in pool]
    return data


def _get_exam(db: Session, exam_id: str) -> WebExam:
    exam = db.get(WebExam, exam_id)
    if not exam:
        raise HTTPException(404, "Exam not found")
    return exam


def _title_taken(db: Session, title: str, except_id: str | None = None) -> bool:
    q = select(WebExam.id).where(func.lower(WebExam.title) == title.strip().lower())
    if except_id:
        q = q.where(WebExam.id != except_id)
    return db.scalar(q) is not None


def _new_exam_id(db: Session, title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:32] or "exam"
    candidate, n = base, 2
    while db.get(WebExam, candidate):
        candidate, n = f"{base}-{n}", n + 1
    return candidate


def _status(a: WebLabAttempt, now: datetime) -> str:
    if a.reset_at:
        return "reset"
    return "locked" if now >= _aware(a.ends_at) else "active"


def _attempt_view(a: WebLabAttempt, now: datetime, quiz_title: str, student: User | None = None) -> dict:
    labs = json.loads(a.labs_json)
    solved = set(json.loads(a.solved_json))
    status = _status(a, now)
    data = {
        "id": a.id,
        "quiz_id": a.quiz_id,
        "quiz_title": quiz_title,
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


def _quiz_title(db: Session, quiz_id: str) -> str:
    exam = db.get(WebExam, quiz_id)
    return exam.title if exam else quiz_id


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
def library(db: Session = Depends(get_db), user: User = Depends(current_user)):
    labs = db.scalars(select(WebLibraryLab).order_by(WebLibraryLab.position, WebLibraryLab.id)).all()
    topics: dict[str, list[dict]] = {}
    for lab in labs:
        topics.setdefault(lab.topic, []).append({"id": lab.id, "title": lab.title, "url": lab.url})
    return {"source": LIBRARY_NOTE, "total": len(labs), "topics": [{"name": n, "labs": ls} for n, ls in topics.items()]}


def _library_lab_view(lab: WebLibraryLab) -> dict:
    return {"id": lab.id, "topic": lab.topic, "title": lab.title, "url": lab.url}


def _url_taken(db: Session, url: str, except_id: int | None = None) -> bool:
    q = select(WebLibraryLab.id).where(WebLibraryLab.url == url)
    if except_id:
        q = q.where(WebLibraryLab.id != except_id)
    return db.scalar(q) is not None


@router.post("/library", status_code=201)
def add_library_lab(data: LibraryLabIn, db: Session = Depends(get_db), user: User = Depends(instructor)):
    if _url_taken(db, data.url):
        raise HTTPException(409, "A lab with this link is already in the library")
    position = (db.scalar(select(func.max(WebLibraryLab.position))) or 0) + 1
    lab = WebLibraryLab(topic=data.topic.strip(), title=data.title.strip(), url=data.url, position=position)
    db.add(lab)
    db.commit()
    return _library_lab_view(lab)


@router.patch("/library/{lab_id}")
def edit_library_lab(lab_id: int, data: LibraryLabUpdate, db: Session = Depends(get_db), user: User = Depends(instructor)):
    lab = db.get(WebLibraryLab, lab_id)
    if not lab:
        raise HTTPException(404, "Lab not found")
    if data.url is not None and _url_taken(db, data.url, except_id=lab.id):
        raise HTTPException(409, "A lab with this link is already in the library")
    for field in ("topic", "title", "url"):
        value = getattr(data, field)
        if value is not None:
            setattr(lab, field, value.strip())
    db.commit()
    return _library_lab_view(lab)


@router.delete("/library/{lab_id}", status_code=204)
def delete_library_lab(lab_id: int, db: Session = Depends(get_db), user: User = Depends(instructor)):
    lab = db.get(WebLibraryLab, lab_id)
    if not lab:
        raise HTTPException(404, "Lab not found")
    db.delete(lab)
    db.commit()


# ---------- Exams: setup (instructor) ----------

@router.get("/quizzes")
def list_exams(db: Session = Depends(get_db), user: User = Depends(current_user)):
    is_instructor = user.role == "instructor"
    q = select(WebExam).order_by(WebExam.position, WebExam.created_at)
    if not is_instructor:
        q = q.where(WebExam.active.is_(True))
    return [_exam_view(db, exam, with_pool=is_instructor) for exam in db.scalars(q).all()]


@router.post("/quizzes", status_code=201)
def create_exam(data: ExamIn, db: Session = Depends(get_db), user: User = Depends(instructor)):
    if _title_taken(db, data.title):
        raise HTTPException(409, "An exam with this title already exists")
    position = (db.scalar(select(func.max(WebExam.position))) or 0) + 1
    exam = WebExam(
        id=_new_exam_id(db, data.title), title=data.title.strip(), description=data.description.strip(),
        duration_minutes=data.duration_minutes, labs_per_attempt=data.labs_per_attempt,
        rules=data.rules.strip(), active=data.active, position=position,
    )
    db.add(exam)
    db.commit()
    return _exam_view(db, exam, with_pool=True)


@router.patch("/quizzes/{exam_id}")
def edit_exam(exam_id: str, data: ExamUpdate, db: Session = Depends(get_db), user: User = Depends(instructor)):
    exam = _get_exam(db, exam_id)
    if data.title is not None and _title_taken(db, data.title, except_id=exam.id):
        raise HTTPException(409, "An exam with this title already exists")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(exam, field, value.strip() if isinstance(value, str) else value)
    db.commit()  # attempts already started keep their own labs and end time
    return _exam_view(db, exam, with_pool=True)


@router.delete("/quizzes/{exam_id}", status_code=204)
def delete_exam(exam_id: str, db: Session = Depends(get_db), user: User = Depends(instructor)):
    exam = _get_exam(db, exam_id)
    if db.scalar(select(WebLabAttempt.id).where(WebLabAttempt.quiz_id == exam_id).limit(1)):
        raise HTTPException(409, "Students have taken this exam, so it is kept for their records. Hide it instead.")
    for lab in _pool(db, exam_id):
        db.delete(lab)
    db.delete(exam)
    db.commit()


@router.post("/quizzes/{exam_id}/labs", status_code=201)
def add_exam_lab(exam_id: str, data: LabIn, db: Session = Depends(get_db), user: User = Depends(instructor)):
    exam = _get_exam(db, exam_id)
    position = (db.scalar(select(func.max(WebExamLab.position)).where(WebExamLab.exam_id == exam_id)) or 0) + 1
    db.add(WebExamLab(exam_id=exam.id, title=data.title.strip(), url=data.url, position=position))
    db.commit()
    return _exam_view(db, exam, with_pool=True)


@router.delete("/quizzes/{exam_id}/labs/{lab_id}")
def remove_exam_lab(exam_id: str, lab_id: int, db: Session = Depends(get_db), user: User = Depends(instructor)):
    exam = _get_exam(db, exam_id)
    lab = db.get(WebExamLab, lab_id)
    if not lab or lab.exam_id != exam_id:
        raise HTTPException(404, "Lab not found in this exam")
    db.delete(lab)
    db.commit()
    return _exam_view(db, exam, with_pool=True)


# ---------- Exams: taking one (student) ----------

@router.post("/quizzes/{quiz_id}/start", status_code=201)
def start_exam(quiz_id: str, response: Response, db: Session = Depends(get_db), user: User = Depends(current_user)):
    exam = db.get(WebExam, quiz_id)
    if not exam or not exam.active:
        raise HTTPException(404, "Exam not found")
    if user.role != "student":
        raise HTTPException(403, "Exams are taken from student accounts")
    now = utcnow()
    current = _open_attempt(db, user.id)
    if current:
        return _existing_exam(db, current, quiz_id, response, now)

    pool = _pool(db, quiz_id)
    if len(pool) < exam.labs_per_attempt:
        raise HTTPException(409, f"This exam has {len(pool)} labs but gives {exam.labs_per_attempt}. Ask the instructor to add labs.")
    labs = [{"title": lab.title, "url": lab.url} for lab in random.sample(pool, exam.labs_per_attempt)]
    a = WebLabAttempt(
        user_id=user.id, quiz_id=quiz_id, labs_json=json.dumps(labs), solved_json="[]",
        started_at=now, ends_at=now + timedelta(minutes=exam.duration_minutes),
    )
    db.add(a)
    db.add(Event(user_id=user.id, kind="web_exam_started"))
    try:
        db.commit()
    except IntegrityError:
        # Another start request for this student won the race; answer with the exam it created.
        db.rollback()
        return _existing_exam(db, _open_attempt(db, user.id), quiz_id, response, now)
    db.refresh(a)
    return _attempt_view(a, now, exam.title)


def _existing_exam(db: Session, current: WebLabAttempt, quiz_id: str, response: Response, now: datetime) -> dict:
    """The student already has an open exam: return it if it is this quiz, otherwise refuse."""
    title = _quiz_title(db, current.quiz_id)
    if current.quiz_id == quiz_id:
        response.status_code = 200  # same exam: a refresh or a second click returns it unchanged
        return _attempt_view(current, now, title)
    if _status(current, now) == "locked":
        raise HTTPException(409, f"Your {title} exam is locked. Ask the instructor to unlock it before starting another exam.")
    raise HTTPException(409, f"You already have {title} open. Finish it before starting another exam.")


@router.get("/attempts/current")
def current_exam(db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = _open_attempt(db, user.id)
    return _attempt_view(a, utcnow(), _quiz_title(db, a.quiz_id)) if a else None


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
    return _attempt_view(a, now, _quiz_title(db, a.quiz_id))


@router.post("/attempts/{attempt_id}/finish")
def finish_exam(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    a = _own_attempt(db, attempt_id, user)
    now = utcnow()
    if _status(a, now) == "active":
        a.ends_at = now
        db.add(Event(user_id=user.id, kind="web_exam_finished"))
        db.commit()
    return _attempt_view(a, now, _quiz_title(db, a.quiz_id))


# ---------- Exams: live view and unlock (instructor) ----------

@router.get("/attempts")
def all_attempts(quiz_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(instructor)):
    q = select(WebLabAttempt, User).join(User, User.id == WebLabAttempt.user_id)
    if quiz_id:
        q = q.where(WebLabAttempt.quiz_id == quiz_id)
    titles = dict(db.execute(select(WebExam.id, WebExam.title)).all())
    now = utcnow()
    rows = db.execute(q.order_by(WebLabAttempt.id.desc()).limit(500)).all()
    return [_attempt_view(a, now, titles.get(a.quiz_id, a.quiz_id), student) for a, student in rows]


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
    return _attempt_view(a, now, _quiz_title(db, a.quiz_id), db.get(User, a.user_id))
