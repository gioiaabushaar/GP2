"""The Alembic migrations must build the same schema as the models, including the Web Labs table."""
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings

BACKEND = Path(__file__).resolve().parents[1]


@pytest.fixture()
def migrated_db(monkeypatch, tmp_path):
    """A fresh SQLite database brought to the latest migration."""
    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    monkeypatch.setattr(settings, "nexis_database_url", url)  # env.py reads the URL from settings
    cfg = Config()  # no ini file, so the test does not reconfigure logging
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    command.upgrade(cfg, "head")
    engine = create_engine(url)
    yield cfg, engine
    engine.dispose()


def test_migrations_create_the_web_labs_table_with_its_one_open_exam_index(migrated_db):
    _, engine = migrated_db
    insp = inspect(engine)
    assert "web_lab_attempts" in insp.get_table_names()
    unique = {i["name"] for i in insp.get_indexes("web_lab_attempts") if i["unique"]}
    assert "uq_web_lab_attempts_one_open_per_user" in unique


def test_migrations_match_the_models(migrated_db):
    cfg, _ = migrated_db
    command.check(cfg)  # fails if a model changed without a migration


def test_new_migrations_can_be_undone(migrated_db):
    cfg, engine = migrated_db
    command.downgrade(cfg, "c62b6d79d532")  # Ali's last migration, before the web labs and deployments tables
    tables = set(inspect(engine).get_table_names())
    assert not tables & {"web_lab_attempts", "web_exams", "web_exam_labs", "web_library_labs", "courses", "lab_deployments"}
    command.upgrade(cfg, "head")
    assert {"web_lab_attempts", "web_exams", "courses", "lab_deployments"} <= set(inspect(engine).get_table_names())


def test_migrations_load_the_default_content(migrated_db):
    from sqlalchemy import text

    _, engine = migrated_db
    with engine.connect() as conn:
        count = lambda table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()  # noqa: E731
        assert (count("web_exams"), count("web_exam_labs"), count("courses")) == (3, 45, 4)
        assert count("web_library_labs") > 200
