from __future__ import annotations

import logging
import re
from collections import Counter

from app.schemas.chunks import ChunkMetadata, PaperChunk, RetrievedChunk

logger = logging.getLogger(__name__)

_HAS_EMBEDDINGS = False
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    _HAS_EMBEDDINGS = True
except ImportError:
    pass

_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def _count_word(term: str, text: str) -> int:
    return len(re.findall(r'\b' + re.escape(term) + r'\b', text))


def _terms(values: list[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        terms.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]+|[一-鿿]{2,}", value.lower()))
    return terms


def _embedding_scores(query: str, chunks: list[PaperChunk]) -> list[float]:
    model = _get_embedding_model()
    query_emb = model.encode([query])
    chunk_texts = [c.content for c in chunks]
    chunk_embs = model.encode(chunk_texts)
    similarities = np.dot(chunk_embs, query_emb.T).flatten()
    norms = np.linalg.norm(chunk_embs, axis=1) * np.linalg.norm(query_emb)
    norms = np.where(norms == 0, 1, norms)
    return (similarities / norms).tolist()


def retrieve_context(
    chunks: list[PaperChunk],
    query: str = "",
    section_hints: list[str] | None = None,
    keywords: list[str] | None = None,
    top_k: int = 6,
) -> list[RetrievedChunk]:
    section_hints = section_hints or []
    keywords = keywords or []
    query_terms = _terms([query])
    keyword_terms = _terms(keywords)
    section_terms = _terms(section_hints)

    results: list[RetrievedChunk] = []
    for chunk in chunks:
        content = chunk.content.lower()
        section_title = (chunk.metadata.section_title or "").lower()
        matched: list[str] = []
        score = 0.0

        for term in section_terms:
            if term in section_title:
                score += 3.0
                matched.append(term)

        counts: Counter[str] = Counter()
        for term in keyword_terms + query_terms:
            count = _count_word(term, content)
            if count:
                counts[term] += count

        for term, count in counts.items():
            score += min(count, 5) * 1.0
            matched.append(term)

        if score > 0:
            results.append(
                RetrievedChunk(
                    content=chunk.content,
                    metadata=chunk.metadata,
                    score=score,
                    matched_terms=sorted(set(matched)),
                )
            )

    if _HAS_EMBEDDINGS and query and chunks:
        try:
            emb_scores = _embedding_scores(query, chunks)
            for r in results:
                idx = r.metadata.chunk_index
                if idx < len(emb_scores):
                    r.score = r.score * 0.4 + emb_scores[idx] * 0.6
            results.sort(key=lambda item: (-item.score, item.metadata.page_start, item.metadata.chunk_index))
        except Exception:
            pass

    results.sort(key=lambda item: (-item.score, item.metadata.page_start, item.metadata.chunk_index))
    return results[:top_k]


def embed_and_store(chunks: list[PaperChunk], paper_id: str) -> bool:
    if not _HAS_EMBEDDINGS or not chunks:
        return False
    try:
        from app.core.database import save_embeddings

        model = _get_embedding_model()
        texts = [c.content for c in chunks]
        embeddings = model.encode(texts, show_progress_bar=False)
        emb_list = []
        for i, emb in enumerate(embeddings):
            emb_bytes = emb.astype("float32").tobytes()
            emb_list.append((i, emb_bytes))
        save_embeddings(paper_id, emb_list)
        return True
    except Exception:
        logger.warning("Failed to embed and store chunks for paper %s", paper_id, exc_info=True)
        return False


def search_knowledge_base(query: str, top_k: int = 10) -> list[RetrievedChunk]:
    if not _HAS_EMBEDDINGS or not query:
        return []

    import numpy as np

    from app.core.database import get_all_embeddings

    rows = get_all_embeddings()
    if not rows:
        return []

    model = _get_embedding_model()
    query_emb = model.encode([query])

    results: list[tuple[float, dict]] = []
    for row in rows:
        chunk_emb = np.frombuffer(row["embedding"], dtype="float32")
        sim = float(np.dot(chunk_emb, query_emb.flatten()))
        norm = float(np.linalg.norm(chunk_emb) * np.linalg.norm(query_emb))
        score = sim / max(norm, 1e-8)
        results.append((score, row))

    results.sort(key=lambda x: -x[0])
    top = results[:top_k]

    output: list[RetrievedChunk] = []
    for score, row in top:
        meta = ChunkMetadata(
            chunk_index=row["chunk_index"],
            page_start=row["page_start"],
            page_end=row["page_end"],
            section_title=row.get("section_title"),
        )
        output.append(
            RetrievedChunk(
                content=row["content"],
                metadata=meta,
                score=score,
                matched_terms=[],
            )
        )
    return output
