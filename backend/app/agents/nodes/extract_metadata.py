from __future__ import annotations

import re

from app.agents.state import PaperAnalysisState
from app.schemas.metadata import PaperMetadata, SectionInfo


def _first_non_empty_lines(text: str, limit: int = 8) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()][:limit]


def _extract_abstract(text: str) -> str:
    match = re.search(
        r"abstract\s*[:.\-]?\s*(.*?)(?:\n\s*(?:1\s+)?introduction|\n\s*keywords|\n\s*index terms)",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return ""
    return " ".join(match.group(1).split())[:1600]


def _extract_keywords(text: str) -> list[str]:
    keyword_match = re.search(r"keywords?\s*[:.\-]?\s*(.*)", text, flags=re.IGNORECASE)
    if keyword_match:
        return [item.strip(" ;,.") for item in keyword_match.group(1).split(",") if item.strip()][:12]

    candidates = [
        "large language model",
        "agent",
        "rag",
        "retrieval",
        "vision",
        "classification",
        "recommendation",
        "benchmark",
        "fine-tuning",
    ]
    lower = text.lower()
    return [item for item in candidates if item in lower][:8]


def extract_metadata_node(state: PaperAnalysisState) -> PaperAnalysisState:
    parsed = state["parsed_paper"]
    first_page = parsed.page_texts[0].text if parsed.page_texts else parsed.raw_text
    lines = _first_non_empty_lines(first_page)
    title = lines[0] if lines else "Untitled Paper"
    author_lines = []
    for line in lines[1:5]:
        if re.match(r"^(abstract|keywords?|index terms)\b", line, flags=re.IGNORECASE):
            break
        author_lines.append(line)
    authors = author_lines[:2]
    abstract = _extract_abstract(parsed.raw_text)
    keywords = _extract_keywords(parsed.raw_text)
    sections = [
        SectionInfo(title=item.title, page_number=item.page_number, level=item.level)
        for item in parsed.section_candidates
    ]

    metadata = PaperMetadata(
        title=title,
        authors=authors,
        abstract=abstract,
        keywords=keywords,
        sections=sections,
    )
    return {"metadata": metadata, "status": "metadata_extracted"}
