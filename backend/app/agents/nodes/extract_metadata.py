from __future__ import annotations

import re

from app.agents.state import PaperAnalysisState
from app.schemas.metadata import PaperMetadata, SectionInfo


TITLE_STOP_PATTERN = re.compile(r"^(abstract|keywords?|index terms|introduction)\b", flags=re.IGNORECASE)
BOILERPLATE_PATTERNS = [
    r"published as a conference paper",
    r"under review",
    r"workshop",
    r"proceedings",
    r"preprint",
    r"arxiv",
    r"openreview",
    r"conference paper",
    r"anonymous",
    r"submission",
]


def _front_matter_lines(text: str, limit: int = 30) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        cleaned = " ".join(line.strip().split())
        if not cleaned:
            continue
        lines.append(cleaned)
        if TITLE_STOP_PATTERN.match(cleaned) or len(lines) >= limit:
            break
    return lines


def _is_boilerplate(line: str) -> bool:
    lower = line.lower()
    return any(re.search(pattern, lower) for pattern in BOILERPLATE_PATTERNS)


def _is_metadata_noise(line: str) -> bool:
    lower = line.lower()
    return (
        _is_boilerplate(line)
        or TITLE_STOP_PATTERN.match(line) is not None
        or "@" in line
        or lower.startswith(("http", "www."))
        or lower in {"supplementary material", "appendix"}
    )


def _title_score(line: str, index: int) -> int:
    if _is_metadata_noise(line) or len(line) < 6 or len(line) > 180:
        return -100

    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]*", line)
    upper_letters = sum(1 for char in line if char.isupper())
    letters = sum(1 for char in line if char.isalpha())
    upper_ratio = upper_letters / max(letters, 1)

    score = 0
    if 3 <= len(words) <= 18:
        score += 3
    if ":" in line:
        score += 4
    if upper_ratio >= 0.35:
        score += 3
    if index <= 8:
        score += 2
    if len(words) <= 2:
        score -= 3
    if "," in line and len(words) <= 8:
        score -= 4
    if re.search(r"\b(university|institute|department|school|lab|labs)\b", line, flags=re.IGNORECASE):
        score -= 4
    return score


def _extract_title_and_index(lines: list[str]) -> tuple[str, int]:
    candidates: list[tuple[int, str, int]] = []
    searchable = [line for line in lines if not TITLE_STOP_PATTERN.match(line)]
    for index, line in enumerate(searchable):
        candidates.append((_title_score(line, index), line, index))
        if index + 1 < len(searchable):
            combined = f"{line} {searchable[index + 1]}"
            candidates.append((_title_score(combined, index) + 1, combined, index))

    candidates = [candidate for candidate in candidates if candidate[0] > -100]
    if not candidates:
        return ("Untitled Paper", 0)

    candidates.sort(key=lambda item: (-item[0], item[2]))
    title = candidates[0][1].strip(" -")
    return (title, candidates[0][2])


def _extract_authors(lines: list[str], title_index: int) -> list[str]:
    authors: list[str] = []
    for line in lines[title_index + 1 : title_index + 6]:
        if TITLE_STOP_PATTERN.match(line):
            break
        if _is_boilerplate(line):
            continue
        if re.search(r"\b(university|institute|department|school|lab|labs)\b", line, flags=re.IGNORECASE):
            continue
        if "@" in line or line.lower().startswith(("http", "www.")):
            continue
        if len(line) > 160:
            continue
        authors.append(line)
    return authors[:2]


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
    lines = _front_matter_lines(first_page)
    title, title_index = _extract_title_and_index(lines)
    authors = _extract_authors(lines, title_index)
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
