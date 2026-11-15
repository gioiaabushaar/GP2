from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.models import Challenge, LabSession, Event, User
from app.core.security import current_user
from app.core.config import settings

router = APIRouter(tags=["Hussam | Docker Lab Management"])

# Only preapproved images built locally are allowed. No untrusted image input.
APPROVED_IMAGES = {"nexis-demo-lab:latest"}

def client_or_503():
    if not settings.nexis_allow_docker:
        raise HTTPException(503, "Docker lab execution disabled. Set NEXIS_ALLOW_DOCKER=true after building the demo image.")
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return client
    except Exception:
        raise HTTPException(503, "Docker Engine is not running or unavailable")

@router.post("/start/{challenge_id}", status_code=201)
def start(challenge_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Challenge, challenge_id)
    if not c or not c.active:
        raise HTTPException(404, "Challenge not found")
    if c.image_name not in APPROVED_IMAGES:
        raise HTTPException(400, "Challenge image is not approved")
    existing = db.scalar(select(LabSession).where(LabSession.user_id == user.id, LabSession.challenge_id == c.id, LabSession.status == "running"))
    if existing:
        raise HTTPException(409, f"Lab session already running: {existing.id}")
    client = client_or_503()
    try:
        container = client.containers.run(
            c.image_name, detach=True, network_disabled=True, read_only=True,
            cap_drop=["ALL"], security_opt=["no-new-privileges:true"],
            mem_limit="128m", nano_cpus=500_000_000, pids_limit=64,
            user="10001:10001", labels={"nexis.managed": "true", "nexis.user_id": str(user.id)},
        )
    except Exception:
        raise HTTPException(503, "Failed to start approved lab image. Run build-demo-lab.ps1 first.")
    try:
        session = LabSession(user_id=user.id, challenge_id=c.id, container_id=container.id, status="running")
        db.add(session)
        db.add(Event(user_id=user.id, challenge_id=c.id, kind="lab_started"))
        db.commit()
        db.refresh(session)
        return {"session_id": session.id, "status": session.status, "container_id": container.id[:12], "note": "Isolated offline demonstration container; no network service is exposed."}
    except Exception:
        container.remove(force=True)
        raise

@router.get("/mine")
def mine(db: Session = Depends(get_db), user: User = Depends(current_user)):
    sessions = db.scalars(select(LabSession).where(LabSession.user_id == user.id).order_by(LabSession.id.desc())).all()
    return [{"id": s.id, "challenge_id": s.challenge_id, "status": s.status, "started_at": s.started_at} for s in sessions]

@router.delete("/{session_id}")
def stop(session_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = db.get(LabSession, session_id)
    if not s or (s.user_id != user.id and user.role != "instructor"):
        raise HTTPException(404, "Lab session not found")
    if s.status == "stopped":
        return {"status": "stopped"}
    client = client_or_503()
    try:
        container = client.containers.get(s.container_id)
        if container.labels.get("nexis.managed") != "true":
            raise HTTPException(403, "Not a managed NEXIS container")
        container.remove(force=True)
    except HTTPException:
        raise
    except Exception:
        # Container might have already been removed; still mark terminated.
        pass
    s.status = "stopped"
    db.add(Event(user_id=user.id, challenge_id=s.challenge_id, kind="lab_stopped"))
    db.commit()
    return {"status": "stopped"}