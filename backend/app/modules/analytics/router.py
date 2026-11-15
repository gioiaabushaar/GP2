from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.models import Challenge, Submission, Event, User
from app.core.security import current_user, instructor

router = APIRouter(tags=["Instructor | Behavioral Analytics"])

@router.get("/me")
def my_activity(db: Session = Depends(get_db), user: User = Depends(current_user)):
    attempts = db.scalar(select(func.count(Submission.id)).where(Submission.user_id == user.id)) or 0
    solved = db.scalar(select(func.count(func.distinct(Submission.challenge_id))).where(Submission.user_id == user.id, Submission.success.is_(True))) or 0
    hints = db.scalar(select(func.count(Event.id)).where(Event.user_id == user.id, Event.kind == "hint_requested")) or 0
    return {"user_id": user.id, "attempts": attempts, "solved_challenges": solved, "hints_used": hints}

@router.get("/instructor/overview")
def instructor_overview(db: Session = Depends(get_db), user: User = Depends(instructor)):
    challenge_count = db.scalar(select(func.count(Challenge.id))) or 0
    student_count = db.scalar(select(func.count(User.id)).where(User.role == "student")) or 0
    attempts = db.scalar(select(func.count(Submission.id))) or 0
    correct = db.scalar(select(func.count(Submission.id)).where(Submission.success.is_(True))) or 0
    hints = db.scalar(select(func.count(Event.id)).where(Event.kind == "hint_requested")) or 0
    return {"students": student_count, "challenges": challenge_count, "submissions": attempts, "correct_submissions": correct, "hints_requested": hints}