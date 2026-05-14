from __future__ import annotations

import re

from app.agents.state import PaperAnalysisState
from app.schemas.citations import CitationInfo

REFERENCE_SECTION_TITLES = {"references", "bibliography", "参考文献", "references cited"}


def _find_reference_chunks(state: PaperAnalysisState) -> str:
    chunked = state.get("chunked_paper")
    if not chunked:
        return ""
    parts: list[str] = []
    for chunk in chunked.chunks:
        title = (chunk.metadata.section_title or "").lower().strip()
        if title in REFERENCE_SECTION_TITLES or "reference" in title:
            parts.append(chunk.content)
    return "\n".join(parts)


def _parse_numbered_references(text: str) -> list[CitationInfo]:
    pattern = re.compile(r"\[(\d+)\]\s*(.+?)(?=\n\s*\[\d+\]|\Z)", re.DOTALL)
    results: list[CitationInfo] = []
    for match in pattern.finditer(text):
        idx = int(match.group(1))
        raw = match.group(2).strip().replace("\n", " ")
        raw = re.sub(r"\s+", " ", raw)
        authors, title, venue, year, doi = _split_reference_parts(raw)
        results.append(CitationInfo(
            index=idx,
            authors=authors,
            title=title,
            venue=venue,
            year=year,
            doi=doi,
            raw_text=raw,
        ))
    return results


def _parse_author_year_references(text: str) -> list[CitationInfo]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    results: list[CitationInfo] = []
    idx = 0
    for line in lines:
        if re.match(r"^\[\d+\]", line):
            continue
        if re.match(r"^[A-Z].*\(\d{4}\)", line) or re.match(r"^[A-Z].*,\s*\d{4}", line):
            idx += 1
            raw = re.sub(r"\s+", " ", line)
            authors, title, venue, year, doi = _split_reference_parts(raw)
            results.append(CitationInfo(
                index=idx,
                authors=authors,
                title=title,
                venue=venue,
                year=year,
                doi=doi,
                raw_text=raw,
            ))
    return results


def _split_reference_parts(raw: str) -> tuple[str, str, str, str, str]:
    doi = ""
    doi_match = re.search(r"(?:doi[:\s]*|https?://doi\.org/)(10\.\d{4,}/[^\s,]+)", raw, re.IGNORECASE)
    if doi_match:
        doi = doi_match.group(1).rstrip(".")

    year = ""
    year_match = re.search(r"\b((?:19|20)\d{2}[a-z]?)\b", raw)
    if year_match:
        year = year_match.group(1)

    authors = ""
    title = ""
    venue = ""

    author_title_match = re.match(r"^(.+?)\.\s+(.+?)(?:\.\s+|[,.]\s+(?:In\s+|Proc|Journal|arXiv|NeurIPS|ICML|ICLR|CVPR|ECCV|AAAI|ACL|EMNLP|NAACL|WWW|KDD|SIGMOD|VLDB|ICDE|CHI))", raw)
    if author_title_match:
        authors = author_title_match.group(1).strip().rstrip(",")
        title = author_title_match.group(2).strip().rstrip(",.")
    else:
        parts = re.split(r"\.\s+", raw, maxsplit=2)
        if len(parts) >= 2:
            authors = parts[0].strip().rstrip(",")
            title = parts[1].strip().rstrip(",.")
        else:
            authors = raw[:80]

    venue_match = re.search(r"(?:In\s+|Proc\.?\s+|Journal\s+of\s+)(.+?)(?:,|\.\s+\d{4}|\Z)", raw)
    if venue_match:
        venue = venue_match.group(1).strip().rstrip(",.")
    elif not venue and parts[-1] if len(parts := raw.split(". ")) > 2 else "":
        venue = parts[-1][:100]

    return authors, title, venue, year, doi


def extract_citations_node(state: PaperAnalysisState) -> PaperAnalysisState:
    ref_text = _find_reference_chunks(state)
    if not ref_text:
        return {"citations": []}

    citations = _parse_numbered_references(ref_text)
    if not citations:
        citations = _parse_author_year_references(ref_text)
    if not citations:
        citations = _fallback_line_split(ref_text)

    return {"citations": citations}


def _fallback_line_split(text: str) -> list[CitationInfo]:
    lines = [line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("---")]
    results: list[CitationInfo] = []
    for idx, line in enumerate(lines, 1):
        raw = re.sub(r"\s+", " ", line)
        if len(raw) < 10:
            continue
        authors, title, venue, year, doi = _split_reference_parts(raw)
        results.append(CitationInfo(
            index=idx,
            authors=authors,
            title=title,
            venue=venue,
            year=year,
            doi=doi,
            raw_text=raw,
        ))
    return results
