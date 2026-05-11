from __future__ import annotations

import re
from collections import Counter

from app.schemas.chunks import PaperChunk, RetrievedChunk


def _terms(values: list[str]) -> list[str]:
    terms: list[str] = []
    for value in values:
        terms.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]+|[\u4e00-\u9fff]{2,}", value.lower()))
    return terms


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

        counts = Counter()
        for term in keyword_terms + query_terms:
            if term in content:
                counts[term] += content.count(term)

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

    results.sort(key=lambda item: (-item.score, item.metadata.page_start, item.metadata.chunk_index))
    return results[:top_k]
