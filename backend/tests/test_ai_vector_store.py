import asyncio
import sqlite3
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.modules.ai_mentor.vector_store import (
    build_index, list_chunks, retrieve_persistent_context,
)


def test_persistent_index_survives_reopen(tmp_path):
    path = tmp_path / "vectors.sqlite3"
    count = build_index(10, "SQL injection in database queries. NEXIS{do_not_store}", path=path)
    assert count > 0
    rows = list_chunks(10, path=path)
    assert rows and not any("NEXIS{do_not_store}" in row["text"] for row in rows)
    assert path.exists()
    assert len(list_chunks(10, path=path)) == len(rows)


def test_index_is_challenge_scoped(tmp_path):
    path = tmp_path / "vectors.sqlite3"
    build_index(1, "Special topic elephant encryption.", path=path)
    build_index(2, "Special topic banana authorization.", path=path)
    first = " ".join(row["text"] for row in list_chunks(1, path=path))
    second = " ".join(row["text"] for row in list_chunks(2, path=path))
    assert "elephant" in first and "banana" not in first
    assert "banana" in second and "elephant" not in second


def test_changed_writeup_invalidates_old_chunks(tmp_path):
    path = tmp_path / "vectors.sqlite3"
    build_index(3, "Legacy specialword alpha.", path=path)
    build_index(3, "Replacement specialword beta.", path=path)
    contents = " ".join(row["text"] for row in list_chunks(3, path=path))
    assert "Replacement" in contents and "Legacy" not in contents


def test_local_retrieval_without_key(tmp_path):
    context, mode = asyncio.run(retrieve_persistent_context(
        5, "SQL injection database", "SQL injection changes database queries.",
        path=tmp_path / "store.sqlite3", top_k=1,
    ))
    assert mode == "persistent-tfidf"
    assert "SQL injection" in context


def test_vector_search_and_embedding_cache(tmp_path):
    path = tmp_path / "store.sqlite3"
    async def fake_embed(texts, api_key):
        return [[1.0, 0.0] if "database" in t.lower() else [0.0, 1.0] for t in texts]
    with patch("app.modules.ai_mentor.vector_store._embed", new=AsyncMock(side_effect=fake_embed)) as mock:
        context, mode = asyncio.run(retrieve_persistent_context(
            6, "database", "Database security requires access controls.", "test-key", path=path, top_k=1
        ))
        assert mode == "sqlite-openai-vector"
        assert "Database" in context
        first_count = len(mock.call_args_list)
        context, mode = asyncio.run(retrieve_persistent_context(
            6, "database", "Database security requires access controls.", "test-key", path=path, top_k=1
        ))
        assert len(mock.call_args_list) == first_count + 1  # query embedding only
