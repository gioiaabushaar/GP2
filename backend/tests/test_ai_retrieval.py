import asyncio
from app.modules.ai_mentor.retrieval import (
    chunks_from_writeup, lexical_rank, retrieve_context, cosine, scrub,
)


def test_scrub_flags():
    assert "NEXIS{secret}" not in scrub("flag: NEXIS{secret}")


def test_chunking():
    chunks = chunks_from_writeup("SQL injection affects queries.\nXSS affects browsers.")
    assert len(chunks) >= 1
    assert "SQL injection" in " ".join(chunks)


def test_local_retrieval_prefers_question_terms():
    docs = ["Linux permissions protect files.", "SQL injection manipulates database queries."]
    selected = lexical_rank("database SQL injection", docs, top_k=1)
    assert selected[0].startswith("SQL injection")


def test_cosine():
    assert cosine([1, 0], [1, 0]) == 1
    assert cosine([1, 0], [0, 1]) == 0


def test_offline_mode_and_no_flag():
    content = "Study authentication concepts.\nNEXIS{should_not_leak}"
    context, mode = asyncio.run(retrieve_context("authentication", content))
    assert mode == "local-tfidf"
    assert "NEXIS{should_not_leak}" not in context

