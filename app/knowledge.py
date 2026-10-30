"""Store knowledge base: load Markdown files, split them into chunks, retrieve.

Two retrievers:
- keyword:   no API calls, works offline (good for first tests)
- embedding: semantic search with a Model Studio embedding model
"""
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Chunk:
    source: str  # e.g. "returns.md#Return window"
    text: str


def load_chunks(kb_dir: Path) -> list[Chunk]:
    """Split every Markdown file on its '## ' headings. One heading = one chunk."""
    chunks: list[Chunk] = []
    for path in sorted(kb_dir.glob("*.md")):
        title = path.stem
        section, lines = None, []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                if section and lines:
                    chunks.append(Chunk(f"{path.name}#{section}", f"{title} / {section}\n" + "\n".join(lines).strip()))
                section, lines = line[3:].strip(), []
            elif section:
                lines.append(line)
        if section and lines:
            chunks.append(Chunk(f"{path.name}#{section}", f"{title} / {section}\n" + "\n".join(lines).strip()))
    return chunks


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class KeywordRetriever:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.docs = [set(_tokens(c.text)) for c in chunks]
        n = len(chunks)
        df: dict[str, int] = {}
        for d in self.docs:
            for t in d:
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log((n + 1) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        q = set(_tokens(query))
        scored = [(c, sum(self.idf.get(t, 0) for t in q & d)) for c, d in zip(self.chunks, self.docs)]
        scored = [s for s in scored if s[1] > 0]
        return sorted(scored, key=lambda s: s[1], reverse=True)[:k]


def cosine(a: list[float], b: list[float]) -> float:
    # TODO(S3): cosine similarity between two vectors
    raise NotImplementedError("TODO(S3): cosine similarity between two vectors")


class EmbeddingRetriever:
    """Embeds all chunks once and caches the vectors in data/.index.json."""

    def __init__(self, chunks: list[Chunk], llm, cache_path: Path, min_score: float = 0.3):
        self.chunks = chunks
        self.llm = llm
        self.min_score = min_score
        fingerprint = hashlib.sha256(
            (llm.settings.embed_model + "".join(c.text for c in chunks)).encode("utf-8")
        ).hexdigest()
        cached = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        if cached.get("fingerprint") == fingerprint:
            self.vectors = cached["vectors"]
        else:
            self.vectors = llm.embed([c.text for c in chunks])
            cache_path.write_text(json.dumps({"fingerprint": fingerprint, "vectors": self.vectors}))

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float]]:
        # TODO(S3): embed the query, score every chunk, return the top k above min_score
        raise NotImplementedError("TODO(S3): embed the query, score every chunk, return the top k above min_score")


def build_retriever(settings, llm):
    chunks = load_chunks(settings.data_dir / "knowledge")
    if settings.retriever == "embedding":
        return EmbeddingRetriever(chunks, llm, settings.data_dir / ".index.json")
    return KeywordRetriever(chunks)
