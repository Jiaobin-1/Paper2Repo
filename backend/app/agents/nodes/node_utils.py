from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from pydantic import BaseModel

from app.schemas.chunks import RetrievedChunk
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


def context_block(chunks: list[RetrievedChunk], max_chars: int = 9000) -> str:
    parts: list[str] = []
    total = 0
    for item in chunks:
        header = (
            f"[chunk {item.metadata.chunk_index}; pages {item.metadata.page_start}-{item.metadata.page_end}; "
            f"section: {item.metadata.section_title or 'unknown'}; score: {item.score:.1f}]"
        )
        text = normalize_space(item.content)
        part = f"{header}\n{text}"
        if total + len(part) > max_chars:
            remaining = max_chars - total
            if remaining <= 200:
                break
            part = part[:remaining]
        parts.append(part)
        total += len(part)
    return "\n\n".join(parts)


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def page_ref(item: RetrievedChunk) -> str:
    section = item.metadata.section_title or "unknown section"
    if item.metadata.page_start == item.metadata.page_end:
        return f"{section}, p.{item.metadata.page_start}"
    return f"{section}, pp.{item.metadata.page_start}-{item.metadata.page_end}"


def evidence_sentence(chunks: list[RetrievedChunk], keywords: Iterable[str], fallback: str = "论文相关片段未明确给出。") -> str:
    lowered_keywords = [keyword.lower() for keyword in keywords]
    for item in chunks:
        sentences = split_sentences(item.content)
        for sentence in sentences:
            lower = sentence.lower()
            if any(keyword in lower for keyword in lowered_keywords):
                return f"{normalize_space(sentence)[:420]}（{page_ref(item)}）"
    if chunks:
        return f"{normalize_space(chunks[0].content)[:420]}（{page_ref(chunks[0])}）"
    return fallback


def extract_sentences(chunks: list[RetrievedChunk], keywords: Iterable[str], limit: int = 4) -> list[str]:
    lowered_keywords = [keyword.lower() for keyword in keywords]
    results: list[str] = []
    seen: set[str] = set()
    for item in chunks:
        for sentence in split_sentences(item.content):
            normalized = normalize_space(sentence)
            if len(normalized) < 20:
                continue
            lower = normalized.lower()
            if any(keyword in lower for keyword in lowered_keywords) and normalized not in seen:
                results.append(f"{normalized[:360]}（{page_ref(item)}）")
                seen.add(normalized)
                if len(results) >= limit:
                    return results
    return results


def split_sentences(text: str) -> list[str]:
    text = normalize_space(text)
    if not text:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", text) if part.strip()]


def llm_or_fallback(
    *,
    system_prompt: str,
    task_prompt: str,
    schema_model: type[BaseModel],
    fallback: BaseModel,
    context: str,
    extra: str = "",
    model_name: str | None = None,
) -> tuple[BaseModel, bool]:
    client = LLMClient(model_name=model_name)
    if not client.is_configured():
        return fallback, False

    user_prompt = f"{task_prompt}\n\n{extra}\n\nPaper context:\n{context}".strip()
    try:
        result = client.structured_output(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_model=schema_model,
        )
        return result, True
    except Exception:
        logger.warning("LLM call failed for %s, using fallback", schema_model.__name__, exc_info=True)
        return fallback, False
