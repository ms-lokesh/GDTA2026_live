import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

from django.conf import settings


DEFAULT_RAG_FILES = [
    "README.md",
    "PRODUCTION_DEPLOYMENT_RUNBOOK.md",
    "docs/DJANGO_API_REFERENCE.md",
    "backend/templates/index.html",
    "backend/templates/program-schedule.html",
    "backend/templates/program-sessions.html",
    "backend/templates/program-safari.html",
    "backend/templates/travel-stay.html",
    "backend/templates/hackathon.html",
    "backend/templates/register.html",
    "backend/templates/register-hackathon.html",
]

STOPWORDS = {
    "a",
    "an",
    "and",
    "the",
    "of",
    "in",
    "to",
    "for",
    "on",
    "with",
    "at",
    "is",
    "are",
    "be",
    "this",
    "that",
    "it",
    "as",
    "or",
    "by",
    "from",
    "can",
    "i",
    "we",
    "you",
    "about",
}


def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z0-9]{2,}", (text or "").lower())
    return [w for w in words if w not in STOPWORDS]


def _strip_html(content: str) -> str:
    text = re.sub(r"<script[\\s\\S]*?</script>", " ", content, flags=re.IGNORECASE)
    text = re.sub(r"<style[\\s\\S]*?</style>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _read_text_file(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    if path.suffix.lower() in {".html", ".htm"}:
        return _strip_html(content)
    return content


def _chunk_text(text: str, chunk_size: int = 700, overlap: int = 120) -> List[str]:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []

    chunks = []
    i = 0
    n = len(text)
    while i < n:
        end = min(n, i + chunk_size)
        part = text[i:end].strip()
        if part:
            chunks.append(part)
        if end >= n:
            break
        i = max(i + 1, end - overlap)
    return chunks


def _source_paths() -> List[Path]:
    root = Path(settings.BASE_DIR).parent
    paths = []
    for rel in DEFAULT_RAG_FILES:
        p = root / rel
        if p.exists() and p.is_file():
            paths.append(p)
    return paths


def _score(query_tokens: List[str], chunk_tokens: List[str]) -> float:
    if not query_tokens or not chunk_tokens:
        return 0.0
    q = set(query_tokens)
    c = set(chunk_tokens)
    overlap = q.intersection(c)
    if not overlap:
        return 0.0
    return (len(overlap) * len(overlap)) / max(1, len(q) * len(c) ** 0.5)


@lru_cache(maxsize=1)
def _build_index() -> List[Dict]:
    index = []
    for path in _source_paths():
        text = _read_text_file(path)
        if not text:
            continue
        for chunk in _chunk_text(text):
            tokens = _tokenize(chunk)
            if not tokens:
                continue
            index.append(
                {
                    "source": str(path),
                    "chunk": chunk,
                    "tokens": tokens,
                }
            )
    return index


def refresh_rag_index():
    _build_index.cache_clear()


def retrieve_context(query: str, top_k: int = 3) -> List[Dict]:
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []

    scored: List[Tuple[float, Dict]] = []
    for row in _build_index():
        s = _score(q_tokens, row["tokens"])
        if s > 0:
            scored.append((s, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"source": item["source"], "text": item["chunk"], "score": score}
        for score, item in scored[:top_k]
    ]


def answer_query(query: str) -> Dict:
    contexts = retrieve_context(query, top_k=3)
    if not contexts:
        return {
            "answer": "I couldn't find that detail in current conference docs. Try asking about schedule, registration, hackathon, travel, or safari.",
            "sources": [],
        }

    answer_lines = ["Here’s what I found from conference documents:"]
    for i, ctx in enumerate(contexts, start=1):
        snippet = ctx["text"][:280].strip()
        if len(ctx["text"]) > 280:
            snippet += "…"
        answer_lines.append(f"{i}. {snippet}")

    # Deduplicate source list while preserving order.
    seen = set()
    sources = []
    for ctx in contexts:
        src = ctx["source"]
        rel_src = src
        try:
            rel_src = os.path.relpath(src, Path(settings.BASE_DIR).parent)
        except Exception:
            pass
        if rel_src not in seen:
            seen.add(rel_src)
            sources.append(rel_src)

    return {
        "answer": "\n".join(answer_lines),
        "sources": sources,
    }
