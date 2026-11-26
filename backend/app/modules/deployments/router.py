"""Courses and one-click lab deployments (instructor only).

Deployment is still simulated: nothing is started on the server until the lab manager's deploy
API (FR6) exists. What is real: the course list, the capacity check and the deployment history,
all stored in the database and managed from the website.
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.models import Challenge, User
from app.core.security import instructor
from app.modules.deployments.models import Course, LabDeployment

router = APIRouter(tags=["Instructor | Courses & deployments"])

# Capacity rule from the GP2 plan: 32 GB host, 4 GB kept for the platform, 256 MB per lab.
HOST_RAM_GB = int(os.getenv("NEXIS_HOST_RAM_GB", "32"))
RESERVED_GB = int(os.getenv("NEXIS_RESERVED_GB", "4"))
LAB_MEMORY_MB = int(os.getenv("NEXIS_LAB_MEMORY_MB", "256"))


def max_labs() -> int:
    return max(0, (HOST_RAM_GB - RESERVED_GB) * 1024 // LAB_MEMORY_MB)


class CourseIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class DeploymentIn(BaseModel):
    course_id: int
    challenge_id: int
    students: int = Field(ge=1, le=5000)


def _course_view(c: Course) -> dict:
    return {"id": c.id, "name": c.name}


def _name_taken(db: Session, name: str, except_id: int | None = None) -> bool:
    q = select(Course.id).where(func.lower(Course.name) == name.strip().lower())
    if except_id:
        q = q.where(Course.id != except_id)
    return db.scalar(q) is not None


# ---------- Courses ----------

@router.get("/courses")
def list_courses(db: Session = Depends(get_db), user: User = Depends(instructor)):
    return [_course_view(c) for c in db.scalars(select(Course).order_by(Course.position, Course.id)).all()]


@router.post("/courses", status_code=201)
def add_course(data: CourseIn, db: Session = Depends(get_db), user: User = Depends(instructor)):
    if _name_taken(db, data.name):
        raise HTTPException(409, "A course with this name already exists")
    position = (db.scalar(select(func.max(Course.position))) or 0) + 1
    c = Course(name=data.name.strip(), position=position)
    db.add(c)
    db.commit()
    return _course_view(c)


@router.patch("/courses/{course_id}")
def rename_course(course_id: int, data: CourseIn, db: Session = Depends(get_db), user: User = Depends(instructor)):
    c = db.get(Course, course_id)
    if not c:
        raise HTTPException(404, "Course not found")
    if _name_taken(db, data.name, except_id=c.id):
        raise HTTPException(409, "A course with this name already exists")
    c.name = data.name.strip()
    db.commit()
    return _course_view(c)


@router.delete("/courses/{course_id}", status_code=204)
def delete_course(course_id: int, db: Session = Depends(get_db), user: User = Depends(instructor)):
    c = db.get(Course, course_id)
    if not c:
        raise HTTPException(404, "Course not found")
    for d in db.scalars(select(LabDeployment).where(LabDeployment.course_id == c.id)).all():
        d.course_id = None  # the history keeps the course name it copied
    db.delete(c)
    db.commit()


# ---------- Deployments ----------

@router.get("/deployments/capacity")
def capacity(user: User = Depends(instructor)):
    return {"host_ram_gb": HOST_RAM_GB, "reserved_gb": RESERVED_GB, "lab_memory_mb": LAB_MEMORY_MB, "max_labs": max_labs()}


def _deployment_view(d: LabDeployment) -> dict:
    return {
        "id": d.id, "course_id": d.course_id, "course_name": d.course_name,
        "challenge_id": d.challenge_id, "challenge_title": d.challenge_title,
        "students": d.students, "status": d.status, "reason": d.reason,
        "created_at": d.created_at.isoformat(),
    }


@router.get("/deployments")
def list_deployments(db: Session = Depends(get_db), user: User = Depends(instructor)):
    rows = db.scalars(select(LabDeployment).order_by(LabDeployment.id.desc()).limit(50)).all()
    return [_deployment_view(d) for d in rows]


@router.post("/deployments", status_code=201)
def deploy(data: DeploymentIn, db: Session = Depends(get_db), user: User = Depends(instructor)):
    course = db.get(Course, data.course_id)
    if not course:
        raise HTTPException(404, "Course not found")
    challenge = db.get(Challenge, data.challenge_id)
    if not challenge:
        raise HTTPException(404, "Challenge not found")
    limit = max_labs()
    if data.students > limit:
        needed_gb = data.students * LAB_MEMORY_MB / 1024
        status, reason = "refused", (
            f"{data.students} labs x {LAB_MEMORY_MB} MB need {needed_gb:.1f} GB. "
            f"This host can run at most {limit} labs at once. Deploy in smaller groups."
        )
    else:
        status, reason = "running", ""
    d = LabDeployment(
        course_id=course.id, course_name=course.name, challenge_id=challenge.id, challenge_title=challenge.title,
        students=data.students, status=status, reason=reason, instructor_id=user.id,
    )
    db.add(d)
    db.commit()
    return _deployment_view(d)
