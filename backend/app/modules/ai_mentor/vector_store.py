"""Persistent, challenge-scoped retrieval for NEXIS AI Mentor.

SQLite persists sanitised knowledge chunks and optional OpenAI embeddings.
Without an API key, search uses deterministic lexical TF-IDF (not semantic search).
No user questions, credentials, or flags are persisted.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path

import httpx

from app.modules.ai_mentor.retrieval import chunks_from_writeup, cosine, lexical_rank, scrub

MODEL = "text-embedding-3-small"
DOCS_DIR = Path(__file__).with_name("knowledge_base")
DEFAULT_STORE = Path(__file__).resolve().parents[3] / ".nexis_ai_vectors.sqlite3"


def _db(path: str | Path | None = None) -> sqlite3.Connection:
    db_path = Path(path or os.environ.get("NEXIS_AI_VECTOR_DB") or DEFAULT_STORE)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path), timeout=10)
    connection.execute("PRAGMA busy_timeout=10000")
    connection.execute("""CREATE TABLE IF NOT EXISTS knowledge_chunks (
        challenge_id INTEGER NOT NULL,
        source TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding TEXT,
        embedding_model TEXT,
        PRIMARY KEY(challenge_id, source, chunk_index)
    )""")
    return connection


def _source_documents(writeup: str) -> list[tuple[str, str]]:
    result = [("challenge-writeup", scrub(writeup))]
    if DOCS_DIR.is_dir():
        for doc in sorted(DOCS_DIR.glob("*.md")):
            result.append((f"knowledge-base/{doc.name}", scrub(doc.read_text(encoding="utf-8"))))
    return result


def build_index(challenge_id: int, writeup: str, *, path: str | Path | None = None) -> int:
    """Incrementally persist safe text chunks, retaining valid cached embeddings."""
    if challenge_id <= 0:
        raise ValueError("challenge_id must be positive")
    total = 0
    with _db(path) as con:
        for source, content in _source_documents(writeup):
            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            parts = chunks_from_writeup(content)
            existing = con.execute(
                "SELECT chunk_index,content_hash,content FROM knowledge_chunks WHERE challenge_id=? AND source=?",
                (challenge_id, source),
            ).fetchall()
            if existing and len(existing) == len(parts) and all(
                index == i and old_hash == content_hash and old_text == parts[i]
                for i, (index, old_hash, old_text) in enumerate(existing)
            ):
                total += len(parts)
                continue
            con.execute("DELETE FROM knowledge_chunks WHERE challenge_id=? AND source=?", (challenge_id, source))
            con.executemany(
                "INSERT INTO knowledge_chunks(challenge_id,source,content_hash,chunk_index,content) VALUES(?,?,?,?,?)",
                [(challenge_id, source, content_hash, i, part) for i, part in enumerate(parts)],
            )
            total += len(parts)
    return total


def list_chunks(challenge_id: int, *, path: str | Path | None = None) -> list[dict]:
    with _db(path) as con:
        rows = con.execute(
            "SELECT source,chunk_index,content,embedding,embedding_model FROM knowledge_chunks "
            "WHERE challenge_id=? ORDER BY source,chunk_index", (challenge_id,)
        ).fetchall()
    return [{"source": src, "index": idx, "text": text,
             "vector": json.loads(vector) if vector else None, "model": model}
            for src, idx, text, vector, model in rows]


async def _embed(texts: list[str], api_key: str) -> list[list[float]]:
    if not texts:
        return []
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": MODEL, "input": texts},
        )
        resp.raise_for_status()
        items = sorted(resp.json()["data"], key=lambda row: row["index"])
    if len(items) != len(texts):
        raise ValueError("Embedding response count mismatch")
    return [item["embedding"] for item in items]


async def retrieve_persistent_context(
    challenge_id: int, question: str, writeup: str, api_key: str = "", *,
    top_k: int = 3, path: str | Path | None = None,
) -> tuple[str, str]:
    """Index challenge-scoped content; search using cached vectors or local TF-IDF."""
    build_index(challenge_id, writeup, path=path)
    rows = list_chunks(challenge_id, path=path)
    if not rows:
        return "Review the relevant challenge concepts.", "no-content"
    limit = max(1, min(top_k, 10))
    mode = "persistent-tfidf"
    selected = lexical_rank(question, [row["text"] for row in rows], top_k=limit)
    if api_key:
        try:
            missing = [row for row in rows if row["vector"] is None or row["model"] != MODEL]
            # Batch only new/changed chunks; existing vectors are reused.
            if missing:
                for start in range(0, len(missing), 64):
                    batch = missing[start:start + 64]
                    vectors = await _embed([row["text"] for row in batch], api_key)
                    with _db(path) as con:
                        for row, vector in zip(batch, vectors):
                            con.execute(
                                "UPDATE knowledge_chunks SET embedding=?, embedding_model=? "
                                "WHERE challenge_id=? AND source=? AND chunk_index=?",
                                (json.dumps(vector), MODEL, challenge_id, row["source"], row["index"]),
                            )
            query_vector = (await _embed([question], api_key))[0]
            rows = list_chunks(challenge_id, path=path)
            ranked = sorted(
                ((cosine(query_vector, row["vector"]), i) for i, row in enumerate(rows)
                 if row["vector"] is not None and len(row["vector"]) == len(query_vector)),
                key=lambda item: (-item[0], item[1]),
            )
            if ranked:
                selected = [rows[i]["text"] for _, i in ranked[:limit]]
                mode = "sqlite-openai-vector"
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, OSError):
            mode = "persistent-tfidf-fallback"
    return scrub(" ".join(selected)[:1100]), mode
