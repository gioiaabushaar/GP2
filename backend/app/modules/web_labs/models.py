"""Web Labs tables. Kept in this module so the shared models.py file did not need to change;
every table here is created by Base.metadata.create_all at startup (or by the Alembic migration)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, event, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import now
from app.modules.web_labs import defaults


class WebExam(Base):
    """A timed web lab exam (the course's PortSwigger quiz). Managed from the instructor's Web Lab Exams page."""

    __tablename__ = "web_exams"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)  # short name used in links, e.g. "quiz-1"
    title: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    duration_minutes: Mapped[int] = mapped_column(Integer)
    labs_per_attempt: Mapped[int] = mapped_column(Integer)
    rules: Mapped[str] = mapped_column(Text, default="")  # one rule per line
    position: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # hidden from students when false
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class WebExamLab(Base):
    """One lab in an exam's pool. Each attempt draws its labs at random from this pool."""

    __tablename__ = "web_exam_labs"
    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[str] = mapped_column(ForeignKey("web_exams.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500))
    position: Mapped[int] = mapped_column(Integer, default=0)


class WebLibraryLab(Base):
    """A lab in the practice library (PortSwigger Web Security Academy by default)."""

    __tablename__ = "web_library_labs"
    id: Mapped[int] = mapped_column(primary_key=True)
    topic: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(500), unique=True)
    position: Mapped[int] = mapped_column(Integer, default=0)


class WebLabAttempt(Base):
    """One student's sitting of a web lab exam. The assigned labs are copied in, so later edits
    to the exam's pool do not change an attempt that already exists."""

    __tablename__ = "web_lab_attempts"
    # At most one open (not yet unlocked) exam per student, enforced by the database itself,
    # so two "start" requests sent at the same moment cannot both create an exam.
    __table_args__ = (
        Index(
            "uq_web_lab_attempts_one_open_per_user", "user_id", unique=True,
            sqlite_where=text("reset_at IS NULL"), postgresql_where=text("reset_at IS NULL"),
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    quiz_id: Mapped[str] = mapped_column(String(40), index=True)
    labs_json: Mapped[str] = mapped_column(Text)  # the assigned labs, in order: [{"title", "url"}]
    solved_json: Mapped[str] = mapped_column(Text, default="[]")  # indexes the student marked as solved
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reset_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)


# Fill each table with the default content once, right after create_all creates it. A table that
# already exists is never touched again, so content the instructor deleted does not come back.
@event.listens_for(WebExam.__table__, "after_create")
def _default_exams(table, connection, **_):
    connection.execute(table.insert(), defaults.exam_rows())


@event.listens_for(WebExamLab.__table__, "after_create")
def _default_exam_labs(table, connection, **_):
    connection.execute(table.insert(), defaults.exam_lab_rows())


@event.listens_for(WebLibraryLab.__table__, "after_create")
def _default_library(table, connection, **_):
    connection.execute(table.insert(), defaults.library_rows())
