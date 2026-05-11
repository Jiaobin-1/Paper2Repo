from __future__ import annotations

import re
from pathlib import Path

from app.schemas.parsed import PageText, ParsedPaper, SectionCandidate


SECTION_PATTERNS = [
    r"^\s*(abstract|introduction|related work|background|method|methodology|approach)\s*$",
    r"^\s*(experiments?|evaluation|results?|discussion|conclusion|limitations?)\s*$",
    r"^\s*(references|appendix)\s*$",
    r"^\s*((\d+|[IVX]+)\.?\s+[A-Z][A-Za-z0-9 ,:/\-()]{2,80})\s*$",
]


def _find_section_candidates(page_number: int, text: str) -> list[SectionCandidate]:
    candidates: list[SectionCandidate] = []
    for line in text.splitlines():
        normalized = " ".join(line.strip().split())
        if not normalized or len(normalized) > 120:
            continue
        for pattern in SECTION_PATTERNS:
            if re.match(pattern, normalized, flags=re.IGNORECASE):
                candidates.append(SectionCandidate(title=normalized, page_number=page_number, level=1))
                break
    return candidates


def parse_pdf(pdf_path: str | Path) -> ParsedPaper:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required. Install backend/requirements.txt first.") from exc

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    page_texts: list[PageText] = []
    sections: list[SectionCandidate] = []
    raw_parts: list[str] = []

    with fitz.open(path) as document:
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            page_texts.append(PageText(page_number=index, text=text))
            raw_parts.append(text)
            sections.extend(_find_section_candidates(index, text))

    return ParsedPaper(
        raw_text="\n\n".join(part for part in raw_parts if part),
        page_texts=page_texts,
        section_candidates=sections,
        page_count=len(page_texts),
    )
