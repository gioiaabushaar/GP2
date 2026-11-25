from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base
from app.core.models import now


class WebLabAttempt(Base):
    """One student's sitting of a timed web lab exam (the course's PortSwigger quiz).

    Kept in this module so the shared models.py file did not need to change. The table is
    created by Base.metadata.create_all at startup, like every other table.
    """

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
