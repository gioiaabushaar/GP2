from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.models import Challenge, Submission, Writeup, Event, User
from app.core.security import current_user, instructor, hash_password, verify_password

router = APIRouter(tags=["Sura | Challenges & Flags"])

class ChallengeCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10)
    category: str = Field(min_length=3, max_length=60)
    difficulty: str = Field(pattern="^(Easy|Medium|Hard)$")
    points: int = Field(ge=10, le=2000)
    flag: str = Field(min_length=8)
    writeup: str = Field(min_length=20)

class FlagSubmit(BaseModel):
    flag: str = Field(min_length=1, max_length=300)

def public_challenge(c: Challenge):
    return {"id": c.id, "title": c.title, "description": c.description, "category": c.category, "difficulty": c.difficulty, "points": c.points}

@router.get("")
def list_challenges(category: str | None = None, difficulty: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = select(Challenge).where(Challenge.active.is_(True))
    if category:
        q = q.where(Challenge.category == category)
    if difficulty:
        q = q.where(Challenge.difficulty == difficulty)
    return [public_challenge(c) for c in db.scalars(q.order_by(Challenge.id)).all()]

@router.get("/{challenge_id}")
def get_challenge(challenge_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Challenge, challenge_id)
    if not c or not c.active:
        raise HTTPException(404, "Challenge not found")
    db.add(Event(user_id=user.id, challenge_id=c.id, kind="challenge_view"))
    db.commit()
    return public_challenge(c)

@router.post("", status_code=201)
def create_challenge(data: ChallengeCreate, db: Session = Depends(get_db), user: User = Depends(instructor)):
    c = Challenge(title=data.title, description=data.description, category=data.category, difficulty=data.difficulty, points=data.points, flag_hash=hash_password(data.flag))
    db.add(c)
    db.flush()
    db.add(Writeup(challenge_id=c.id, content=data.writeup, source="Instructor-created content"))
    db.commit()
    db.refresh(c)
    return public_challenge(c)

@router.post("/{challenge_id}/submit")
def submit_flag(challenge_id: int, data: FlagSubmit, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Challenge, challenge_id)
    if not c or not c.active:
        raise HTTPException(404, "Challenge not found")
    correct = verify_password(data.flag, c.flag_hash)
    db.add(Submission(user_id=user.id, challenge_id=c.id, success=correct))
    db.add(Event(user_id=user.id, challenge_id=c.id, kind="flag_correct" if correct else "flag_wrong"))
    db.commit()
    return {"correct": correct, "message": "Challenge solved" if correct else "Incorrect flag"}