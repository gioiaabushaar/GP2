import asyncio

import logging
import os
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db, SessionLocal
from app.core.models import Challenge, LabSession, Event, User
from app.core.security import current_user
from app.core.config import settings

log = logging.getLogger("nexis.labs")
router = APIRouter(tags=["Hussam | Docker Lab Management"])

# Only preapproved images built locally are allowed. No untrusted image input.
APPROVED_IMAGES = {"nexis-demo-lab:latest"}

# FR2: a lab is removed automatically after this many minutes (override with NEXIS_LAB_TTL_MINUTES).
LAB_TTL_MINUTES = int(os.getenv("NEXIS_LAB_TTL_MINUTES", "60"))

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


def _aware(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC so comparisons are consistent."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def _remove_container(client, container_id: str) -> None:
    """Remove a managed container. A container that is already gone is fine; any other failure is raised."""
    from docker.errors import NotFound
    try:
        container = client.containers.get(container_id)
    except NotFound:
        return
    if container.labels.get("nexis.managed") != "true":
        raise HTTPException(403, "Not a managed NEXIS container")
    container.remove(force=True)

def reap_expired(db: Session, client) -> int:
    """Remove running labs older than LAB_TTL_MINUTES and mark them expired. Returns how many were removed."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=LAB_TTL_MINUTES)
    reaped = 0
    for s in db.scalars(select(LabSession).where(LabSession.status == "running")).all():
        if _aware(s.started_at) > cutoff:
            continue
        try:
            _remove_container(client, s.container_id)
        except Exception:
            log.exception("Could not remove expired lab %s; it will be retried", s.id)
            continue
        s.status = "expired"
        db.add(Event(user_id=s.user_id, challenge_id=s.challenge_id, kind="lab_expired"))
        reaped += 1
    if reaped:
        db.commit()
    return reaped

def _reap_if_docker_available(db: Session) -> None:
    if not settings.nexis_allow_docker:
        return
    try:
        reap_expired(db, client_or_503())
    except Exception:
        log.exception("Expired-lab cleanup skipped")

@router.post("/start/{challenge_id}", status_code=201)
def start(challenge_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Challenge, challenge_id)
    if not c or not c.active:
        raise HTTPException(404, "Challenge not found")
    if c.image_name not in APPROVED_IMAGES:
        raise HTTPException(400, "Challenge image is not approved")
    client = client_or_503()
    reap_expired(db, client)
    existing = db.scalar(select(LabSession).where(LabSession.user_id == user.id, LabSession.status == "running"))
    if existing:
        raise HTTPException(409, f"Lab session already running: {existing.id}. Stop it before starting another.")
    started = time.monotonic()
    try:
        container = client.containers.run(
            c.image_name, detach=True, network_disabled=True, read_only=True,
            cap_drop=["ALL"], security_opt=["no-new-privileges:true"],
            mem_limit="128m", nano_cpus=500_000_000, pids_limit=64,
            user="10001:10001", labels={"nexis.managed": "true", "nexis.user_id": str(user.id)},
        )
    except Exception:
        log.exception("Lab image failed to start")
        raise HTTPException(503, "Failed to start approved lab image. Run build-demo-lab.ps1 first.")
    provision_seconds = round(time.monotonic() - started, 2)
    if provision_seconds > 30:
        log.warning("Lab took %.1fs to start (FR1 target: 30s)", provision_seconds)
    try:
        session = LabSession(user_id=user.id, challenge_id=c.id, container_id=container.id, status="running")
        db.add(session)
        db.add(Event(user_id=user.id, challenge_id=c.id, kind="lab_started"))
        db.commit()
        db.refresh(session)
        return {"session_id": session.id, "status": session.status, "container_id": container.id[:12], "provision_seconds": provision_seconds, "expires_in_minutes": LAB_TTL_MINUTES, "note": "Isolated offline demonstration container; no network service is exposed."}
    except Exception:
        container.remove(force=True)
        raise

@router.get("/mine")
def mine(db: Session = Depends(get_db), user: User = Depends(current_user)):
    _reap_if_docker_available(db)
    sessions = db.scalars(select(LabSession).where(LabSession.user_id == user.id).order_by(LabSession.id.desc())).all()
    return [{"id": s.id, "challenge_id": s.challenge_id, "status": s.status, "started_at": s.started_at} for s in sessions]

@router.delete("/{session_id}")
def stop(session_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    s = db.get(LabSession, session_id)
    if not s or (s.user_id != user.id and user.role != "instructor"):
        raise HTTPException(404, "Lab session not found")
    if s.status != "running":
        return {"status": s.status}
    client = client_or_503()
    try:
        _remove_container(client, s.container_id)
    except HTTPException:
        raise
    except Exception:
        log.exception("Could not remove container for lab %s", s.id)
        raise HTTPException(503, "Could not stop the lab container. Please try again.")
    s.status = "stopped"
    db.add(Event(user_id=user.id, challenge_id=s.challenge_id, kind="lab_stopped"))
    db.commit()
    return {"status": "stopped"}


REAPER_INTERVAL_SECONDS = int(os.getenv("NEXIS_REAPER_INTERVAL_SECONDS", "60"))


def _reap_once() -> int:
    """One cleanup pass using its own DB session (runs outside any request)."""
    if not settings.nexis_allow_docker:
        return 0
    with SessionLocal() as db:
        return reap_expired(db, client_or_503())
async def reaper_loop() -> None:
    """Background task: remove expired labs even when nobody calls the API (FR2)."""
    while True:
        await asyncio.sleep(REAPER_INTERVAL_SECONDS)
        try:
            await asyncio.to_thread(_reap_once)
        except HTTPException:
            log.warning("Reaper skipped: Docker unavailable")
        except Exception:
            log.exception("Background reaper pass failed; will retry")
            