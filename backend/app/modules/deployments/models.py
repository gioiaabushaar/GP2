"""Courses and one-click deployment records, used by the instructor's Deploy Labs page."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import now

DEFAULT_COURSES = ["Network Security Basics", "Web Application Security", "Cryptography Fundamentals", "Digital Forensics"]


class Course(Base):
    __tablename__ = "courses"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class LabDeployment(Base):
    """One deployment request. Course and challenge names are copied in, so the history still
    reads correctly after a course is renamed or deleted."""

    __tablename__ = "lab_deployments"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    course_name: Mapped[str] = mapped_column(String(120))
    challenge_id: Mapped[int | None] = mapped_column(ForeignKey("challenges.id", ondelete="SET NULL"), nullable=True)
    challenge_title: Mapped[str] = mapped_column(String(150))
    students: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))  # "running" or "refused"
    reason: Mapped[str] = mapped_column(Text, default="")
    instructor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


@event.listens_for(Course.__table__, "after_create")
def _default_courses(table, connection, **_):
    # Filled once when the table is created; instructors manage courses from the website afterwards.
    connection.execute(table.insert(), [{"name": n, "position": i} for i, n in enumerate(DEFAULT_COURSES)])
