"""Initial Web Labs content, written into the database once, when its tables are first created.

After that the database is the only source: instructors change exams and the library from the
website, and nothing here is read again. Used by the table-creation hooks in models.py and by the
Alembic migration, so both ways of creating a database start with the same content.
"""
import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).parent / "data"


@lru_cache
def _exams_file() -> dict:
    return json.loads((DATA / "default_exams.json").read_text(encoding="utf-8"))


def exam_rows() -> list[dict]:
    doc = _exams_file()
    rules = "\n".join(doc["rules"])
    return [
        {
            "id": q["id"], "title": q["title"], "description": q["description"],
            "duration_minutes": q["duration_minutes"], "labs_per_attempt": q["labs_per_attempt"],
            "rules": rules, "position": i, "active": True,
        }
        for i, q in enumerate(doc["quizzes"])
    ]


def exam_lab_rows() -> list[dict]:
    return [
        {"exam_id": q["id"], "title": lab["title"], "url": lab["url"], "position": i}
        for q in _exams_file()["quizzes"]
        for i, lab in enumerate(q["pool"])
    ]


def library_rows() -> list[dict]:
    labs = json.loads((DATA / "default_library.json").read_text(encoding="utf-8"))["labs"]
    return [{"topic": lab["topic"], "title": lab["title"], "url": lab["url"], "position": i} for i, lab in enumerate(labs)]
