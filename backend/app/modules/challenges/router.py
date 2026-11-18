from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.models import Challenge, Submission, Writeup, Event, User
from app.core.security import current_user, instructor, hash_password, verify_password

router = APIRouter(tags=["Sura | Challenges & Flags"])

# Fixed lists so every challenge is classified the same way (FR3 / FR11).
Category = Literal["Web", "Network", "Forensics", "Cryptography", "Reverse Engineering"]
Difficulty = Literal["Easy", "Medium", "Hard"]
DEFAULT_POINTS = {"Easy": 100, "Medium": 200, "Hard": 300}
FLAG_FORMAT = r"^NEXIS\{[^{}\s]{3,200}\}$"  # e.g. NEXIS{caesar_shift_3}


class ChallengeCreate(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{
        "title": "Caesar Cipher Breaker",
        "description": "Recover the hidden message that was encrypted with a simple letter shift.",
        "category": "Cryptography",
        "difficulty": "Easy",
        "points": 150,
        "flag": "NEXIS{caesar_shift_3}",
        "writeup": "A Caesar cipher shifts every letter by the same amount. Trying all 25 shifts reveals the message.",
    }]}}
    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=10)
    category: Category
    difficulty: Difficulty
    points: int | None = Field(default=None, ge=10, le=2000, description="Leave empty to use the default for the difficulty: Easy 100, Medium 200, Hard 300.")
    flag: str = Field(pattern=FLAG_FORMAT, description="Must look like NEXIS{...} with no spaces.")
    writeup: str = Field(min_length=20, description="Reference solution used by the AI mentor for hints. Never shown to students.")


class FlagSubmit(BaseModel):
    model_config = {"json_schema_extra": {"examples": [{"flag": "NEXIS{caesar_shift_3}"}]}}
    flag: str = Field(min_length=1, max_length=300)


def public_challenge(c: Challenge, solved: bool | None = None):
    data = {"id": c.id, "title": c.title, "description": c.description, "category": c.category, "difficulty": c.difficulty, "points": c.points}
    if solved is not None:
        data["solved"] = solved
    return data


def solved_ids(db: Session, user_id: int) -> set[int]:
    q = select(Submission.challenge_id).where(Submission.user_id == user_id, Submission.success.is_(True)).distinct()
    return set(db.scalars(q).all())


def total_score(db: Session, user_id: int) -> int:
    # Each solved challenge counts once, however many times its flag was sent.
    ids = select(Submission.challenge_id).where(Submission.user_id == user_id, Submission.success.is_(True)).distinct()
    return db.scalar(select(func.coalesce(func.sum(Challenge.points), 0)).where(Challenge.id.in_(ids))) or 0


@router.get("")
def list_challenges(category: Category | None = None, difficulty: Difficulty | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    q = select(Challenge).where(Challenge.active.is_(True))
    if category:
        q = q.where(Challenge.category == category)
    if difficulty:
        q = q.where(Challenge.difficulty == difficulty)
    done = solved_ids(db, user.id)
    return [public_challenge(c, c.id in done) for c in db.scalars(q.order_by(Challenge.id)).all()]


# Fixed paths must be declared before "/{challenge_id}", or FastAPI would treat "my-score" as an id.
@router.get("/my-score")
def my_score(db: Session = Depends(get_db), user: User = Depends(current_user)):
    first_solve = (select(Submission.challenge_id, func.min(Submission.submitted_at).label("solved_at"))
                   .where(Submission.user_id == user.id, Submission.success.is_(True))
                   .group_by(Submission.challenge_id).subquery())
    rows = db.execute(select(Challenge.id, Challenge.title, Challenge.points, first_solve.c.solved_at)
                      .join(first_solve, first_solve.c.challenge_id == Challenge.id)
                      .order_by(first_solve.c.solved_at)).all()
    solved = [{"challenge_id": r.id, "title": r.title, "points": r.points, "solved_at": r.solved_at} for r in rows]
    return {"user_id": user.id, "total_score": sum(s["points"] for s in solved), "solved_count": len(solved), "solved": solved}


@router.get("/leaderboard")
def leaderboard(db: Session = Depends(get_db), user: User = Depends(instructor)):
    solved = select(Submission.user_id, Submission.challenge_id).where(Submission.success.is_(True)).distinct().subquery()
    score = func.coalesce(func.sum(Challenge.points), 0).label("total_score")
    rows = db.execute(select(User.id, User.full_name, score, func.count(Challenge.id).label("solved_count"))
                      .select_from(User)
                      .outerjoin(solved, solved.c.user_id == User.id)
                      .outerjoin(Challenge, Challenge.id == solved.c.challenge_id)
                      .where(User.role == "student")
                      .group_by(User.id, User.full_name)
                      .order_by(desc("total_score"), User.full_name)).all()
    return [{"rank": i, "user_id": r.id, "full_name": r.full_name, "total_score": r.total_score, "solved_count": r.solved_count} for i, r in enumerate(rows, start=1)]


@router.get("/{challenge_id}")
def get_challenge(challenge_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Challenge, challenge_id)
    if not c or not c.active:
        raise HTTPException(404, "Challenge not found")
    db.add(Event(user_id=user.id, challenge_id=c.id, kind="challenge_view"))
    db.commit()
    return public_challenge(c, c.id in solved_ids(db, user.id))


@router.post("", status_code=201)
def create_challenge(data: ChallengeCreate, db: Session = Depends(get_db), user: User = Depends(instructor)):
    title = data.title.strip()
    if db.scalar(select(Challenge).where(func.lower(Challenge.title) == title.lower())):
        raise HTTPException(409, "A challenge with this title already exists")
    points = data.points if data.points is not None else DEFAULT_POINTS[data.difficulty]
    # Only a hash of the flag is stored, like a password, so a database leak does not reveal answers.
    c = Challenge(title=title, description=data.description, category=data.category, difficulty=data.difficulty, points=points, flag_hash=hash_password(data.flag))
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
    correct = verify_password(data.flag.strip(), c.flag_hash)
    attempts = db.scalar(select(func.count(Submission.id)).where(Submission.user_id == user.id, Submission.challenge_id == c.id)) or 0

    if c.id in solved_ids(db, user.id):
        # Already solved: answer, but do not store another attempt or give points twice.
        return {"correct": correct, "already_solved": True, "points_awarded": 0, "total_score": total_score(db, user.id),
                "attempt_number": attempts, "message": "You already solved this challenge. No extra points."}

    db.add(Submission(user_id=user.id, challenge_id=c.id, success=correct))
    db.add(Event(user_id=user.id, challenge_id=c.id, kind="flag_correct" if correct else "flag_wrong"))
    db.commit()
    awarded = c.points if correct else 0
    return {"correct": correct, "already_solved": False, "points_awarded": awarded, "total_score": total_score(db, user.id),
            "attempt_number": attempts + 1, "message": f"Correct flag! +{awarded} points" if correct else "Incorrect flag. Try again."}
