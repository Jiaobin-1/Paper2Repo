from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

from app.schemas.chunks import ChunkMetadata, PaperChunk, RetrievedChunk

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]+|[\u3400-\u9fff]{2,}")
_CJK_RE = re.compile(r"[\u3400-\u9fff]")

_HAS_EMBEDDINGS = False
try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    _HAS_EMBEDDINGS = True
except ImportError:
    pass

_embedding_model = None
EmbeddingCache = dict[str, Any]


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def new_embedding_cache() -> EmbeddingCache:
    return {"chunk_key": None, "chunk_embeddings": None, "query_embeddings": {}}


def _count_word(term: str, text: str) -> int:
    if _CJK_RE.search(term):
        return text.count(term)
    return len(re.findall(r"\b" + re.escape(term) + r"\b", text))


def _terms(values: list[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        for match in _TOKEN_RE.finditer(value.lower()):
            token = match.group(0)
            if _CJK_RE.search(token) and len(token) > 2:
                terms.extend(token[index : index + 2] for index in range(len(token) - 1))
            else:
                terms.append(token)
    return terms


def _chunks_key(chunks: list[PaperChunk]) -> tuple[tuple[int, int], ...]:
    return tuple((chunk.metadata.chunk_index, hash(chunk.content)) for chunk in chunks)


def _encode_query(model: Any, query: str):
    encoded = model.encode([query], show_progress_bar=False)
    vector = np.asarray(encoded, dtype="float32").reshape(-1)
    if vector.size == 0:
        raise ValueError("Embedding model returned an empty query vector.")
    return vector


def _encode_chunks(model: Any, chunks: list[PaperChunk]):
    encoded = model.encode([chunk.content for chunk in chunks], show_progress_bar=False)
    matrix = np.asarray(encoded, dtype="float32")
    if matrix.ndim != 2 or matrix.shape[0] != len(chunks) or matrix.shape[1] == 0:
        raise ValueError("Embedding model returned an invalid chunk matrix.")
    return matrix


def _embedding_scores(query: str, chunks: list[PaperChunk], cache: EmbeddingCache | None = None) -> list[float]:
    model = _get_embedding_model()
    if cache is not None:
        query_cache = cache.setdefault("query_embeddings", {})
        query_vector = query_cache.get(query)
        if query_vector is None:
            query_vector = _encode_query(model, query)
            query_cache[query] = query_vector
        else:
            query_vector = np.asarray(query_vector, dtype="float32").reshape(-1)
        key = _chunks_key(chunks)
        if cache.get("chunk_key") != key or cache.get("chunk_embeddings") is None:
            cache["chunk_key"] = key
            cache["chunk_embeddings"] = _encode_chunks(model, chunks)
        chunk_matrix = np.asarray(cache["chunk_embeddings"], dtype="float32")
        if (
            chunk_matrix.ndim != 2
            or chunk_matrix.shape[0] != len(chunks)
            or chunk_matrix.shape[1] != query_vector.size
        ):
            # Persisted vectors may be incomplete or produced by a model with a
            # different dimension. Re-encode the current chunks rather than
            # dropping semantic retrieval for the request.
            chunk_matrix = _encode_chunks(model, chunks)
            cache["chunk_key"] = key
            cache["chunk_embeddings"] = chunk_matrix
    else:
        query_vector = _encode_query(model, query)
        chunk_matrix = _encode_chunks(model, chunks)

    similarities = chunk_matrix @ query_vector
    norms = np.linalg.norm(chunk_matrix, axis=1) * np.linalg.norm(query_vector)
    scores = similarities / np.maximum(norms, 1e-8)
    scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(scores, 0.0, 1.0).tolist()


def load_stored_embedding_cache(paper_id: str, chunks: list[PaperChunk]) -> EmbeddingCache:
    cache = new_embedding_cache()
    if not _HAS_EMBEDDINGS or not chunks:
        return cache

    from app.core.database import get_paper_embeddings

    rows = get_paper_embeddings(paper_id)
    if len(rows) != len(chunks):
        return cache

    expected_indices = [chunk.metadata.chunk_index for chunk in chunks]
    if len(set(expected_indices)) != len(expected_indices):
        return cache

    try:
        vectors_by_index: dict[int, Any] = {}
        for row in rows:
            chunk_index = int(row["chunk_index"])
            if chunk_index in vectors_by_index:
                return cache
            vector = np.frombuffer(row["embedding"], dtype="float32")
            if vector.size == 0 or not np.all(np.isfinite(vector)):
                return cache
            vectors_by_index[chunk_index] = vector

        if set(vectors_by_index) != set(expected_indices):
            return cache

        dimensions = {vector.size for vector in vectors_by_index.values()}
        if len(dimensions) != 1:
            return cache

        matrix = np.stack([vectors_by_index[index] for index in expected_indices])
    except (BufferError, TypeError, ValueError):
        logger.warning("Ignoring invalid stored embeddings for paper %s", paper_id, exc_info=True)
        return cache

    cache["chunk_key"] = _chunks_key(chunks)
    cache["chunk_embeddings"] = matrix
    return cache


def retrieve_context(
    chunks: list[PaperChunk],
    query: str = "",
    section_hints: list[str] | None = None,
    keywords: list[str] | None = None,
    top_k: int = 6,
    embedding_cache: EmbeddingCache | None = None,
) -> list[RetrievedChunk]:
    section_hints = section_hints or []
    keywords = keywords or []
    query_terms = _terms([query])
    keyword_terms = _terms(keywords)
    section_terms = _terms(section_hints)

    lexical_scores: list[float] = []
    matched_terms: list[list[str]] = []
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

        lexical_scores.append(score)
        matched_terms.append(sorted(set(matched)))

    embedding_scores: list[float] | None = None
    if _HAS_EMBEDDINGS and query and chunks:
        try:
            candidate_scores = _embedding_scores(query, chunks, embedding_cache)
            if len(candidate_scores) != len(chunks):
                raise ValueError("Embedding score count does not match chunk count.")
            embedding_scores = candidate_scores
        except Exception:
            logger.warning("Semantic retrieval failed; using lexical scores", exc_info=True)

    results: list[RetrievedChunk] = []
    for position, chunk in enumerate(chunks):
        lexical_score = lexical_scores[position]
        score = lexical_score
        if embedding_scores is not None:
            score = lexical_score * 0.4 + embedding_scores[position] * 0.6
        if score <= 0:
            continue
        results.append(
            RetrievedChunk(
                content=chunk.content,
                metadata=chunk.metadata,
                score=score,
                matched_terms=matched_terms[position],
            )
        )

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

    try:
        model = _get_embedding_model()
        query_emb = _encode_query(model, query)
    except Exception:
        logger.warning("Knowledge-base query embedding failed", exc_info=True)
        return []

    valid_rows: list[dict[str, Any]] = []
    vectors: list[Any] = []
    for row in rows:
        try:
            vector = np.frombuffer(row["embedding"], dtype="float32")
        except (BufferError, TypeError, ValueError):
            logger.warning("Skipping an invalid stored knowledge-base embedding", exc_info=True)
            continue
        if vector.size != query_emb.size or not np.all(np.isfinite(vector)):
            continue
        valid_rows.append(row)
        vectors.append(vector)

    if not vectors:
        return []

    # Stack all valid stored embeddings into one matrix and score them in a
    # single vectorized pass instead of a per-row Python loop.
    chunk_matrix = np.stack(vectors)
    query_norm = float(np.linalg.norm(query_emb))
    sims = chunk_matrix @ query_emb
    norms = np.linalg.norm(chunk_matrix, axis=1) * query_norm
    scores = sims / np.maximum(norms, 1e-8)
    scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
    scores = np.clip(scores, 0.0, 1.0)

    order = np.argsort(-scores)[:top_k]

    output: list[RetrievedChunk] = []
    for i in order:
        row = valid_rows[int(i)]
        score = float(scores[int(i)])
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
                paper_id=row["paper_id"],
                paper_title=row.get("paper_title"),
            )
        )
    return output
