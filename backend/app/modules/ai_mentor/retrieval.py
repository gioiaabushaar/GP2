"""NEXIS AI Mentor retrieval: embeddings when configured, local TF-IDF fallback.

No flags or secrets are persisted. Chunk contents come from existing curated writeups.
"""
import math
import re
from collections import Counter

import httpx

TOKEN = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]{2,}")
FLAG = re.compile(r"NEXIS\{[^}]+\}|flag\s*[:=]\s*\S+", re.IGNORECASE)


def scrub(text: str) -> str:
    return FLAG.sub("[redacted]", text)


def chunks_from_writeup(content: str, max_chars: int = 480) -> list[str]:
    # Split sentence-by-sentence then pack into reasonably sized chunks.
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+|\n+", content) if x.strip()]
    chunks = []
    buf = ""
    for sentence in sentences:
        sentence = scrub(sentence)
        if len(sentence) > max_chars:
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.extend(sentence[i:i + max_chars] for i in range(0, len(sentence), max_chars))
        elif len(buf) + len(sentence) + 1 > max_chars:
            chunks.append(buf)
            buf = sentence
        else:
            buf = (buf + " " + sentence).strip()
    if buf:
        chunks.append(buf)
    return chunks


def _tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def lexical_rank(question: str, chunks: list[str], top_k: int = 3) -> list[str]:
    """TF-IDF cosine ranking. Deterministic fallback, not semantic embeddings."""
    if not chunks:
        return []
    docs = [Counter(_tokens(x)) for x in chunks]
    query = Counter(_tokens(question))
    if not query:
        return chunks[:top_k]
    df = Counter(term for doc in docs for term in doc)
    n = len(docs)

    def vector(counts):
        return {term: (1 + math.log(freq)) * (1 + math.log((n + 1) / (df[term] + 1)))
                for term, freq in counts.items() if freq > 0}

    qv = vector(query)
    qnorm = math.sqrt(sum(x * x for x in qv.values())) or 1
    scores = []
    for i, doc in enumerate(docs):
        dv = vector(doc)
        norm = math.sqrt(sum(x * x for x in dv.values())) or 1
        score = sum(weight * dv.get(term, 0) for term, weight in qv.items()) / (qnorm * norm)
        scores.append((score, i))
    scores.sort(key=lambda item: (-item[0], item[1]))
    return [chunks[i] for _, i in scores[:top_k]]


def cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    denom = math.sqrt(sum(v*v for v in a)) * math.sqrt(sum(v*v for v in b))
    return sum(x*y for x, y in zip(a, b)) / denom if denom else 0.0


async def semantic_rank(question: str, chunks: list[str], api_key: str, top_k: int = 3) -> list[str]:
    """OpenAI embeddings provide actual semantic search when an API key exists."""
    if not chunks:
        return []
    async with httpx.AsyncClient(timeout=25.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "text-embedding-3-small", "input": [question, *chunks]},
        )
        response.raise_for_status()
        items = sorted(response.json()["data"], key=lambda x: x["index"])
        vectors = [item["embedding"] for item in items]
        if len(vectors) != len(chunks) + 1:
            raise ValueError("Embedding count mismatch")
        scores = [(cosine(vectors[0], vec), i) for i, vec in enumerate(vectors[1:])]
        scores.sort(key=lambda item: (-item[0], item[1]))
        return [chunks[i] for _, i in scores[:top_k]]


async def retrieve_context(question: str, content: str, api_key: str = "", top_k: int = 3) -> tuple[str, str]:
    chunks = chunks_from_writeup(content)
    if not chunks:
        return "Review the relevant challenge concepts.", "no-content"
    mode = "local-tfidf"
    chosen = lexical_rank(question, chunks, top_k=top_k)
    if api_key:
        try:
            chosen = await semantic_rank(question, chunks, api_key, top_k=top_k)
            mode = "openai-embeddings"
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
            mode = "local-tfidf-fallback"
    return scrub(" ".join(chosen)[:1100]), mode

