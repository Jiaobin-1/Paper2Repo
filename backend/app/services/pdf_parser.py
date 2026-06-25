from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.schemas.parsed import PageText, ParsedPaper, SectionCandidate

logger = logging.getLogger(__name__)

SECTION_PATTERNS = [
    r"^\s*(abstract|introduction|related work|background|method|methodology|approach)\s*$",
    r"^\s*(experiments?|evaluation|results?|discussion|conclusion|limitations?)\s*$",
    r"^\s*(references|appendix)\s*$",
    r"^\s*((\d+|[IVX]+)\.?\s+[A-Z][A-Za-z0-9 ,:/\-()]{2,80})\s*$",
]

_MATH_SYMBOLS = set("=∑∏∫√≤≥≈≠±×÷∂∇∞∈∉⊂⊆∪∩→←↔")
_MATH_TERMS = re.compile(r"\\(?:sum|prod|int|frac|sqrt|mathcal|mathbf)|\b(?:argmax|argmin|softmax|log|exp)\b")
_EQUATION_NUMBER = re.compile(r"\(\s*\d+[a-z]?\s*\)\s*$", re.IGNORECASE)
_MAX_TABLES_PER_PAGE = 8
_MAX_TABLE_ROWS = 80
_MAX_TABLE_COLUMNS = 20
_ocr_unavailable_logged = False


class PdfPageLimitError(RuntimeError):
    pass


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


def parse_pdf(pdf_path: str | Path, *, max_pages: int | None = None) -> ParsedPaper:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required. Install backend/requirements.txt first.") from exc

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    settings = get_settings()
    page_texts: list[PageText] = []
    sections: list[SectionCandidate] = []
    raw_parts: list[str] = []
    ocr_page_count = 0
    table_count = 0
    formula_count = 0

    try:
        with fitz.open(path) as document:
            page_limit = max(1, max_pages or settings.pdf_max_pages)
            if document.page_count > page_limit:
                raise PdfPageLimitError(
                    f"PDF has {document.page_count} pages, exceeding the configured limit of {page_limit}."
                )
            for index, page in enumerate(document, start=1):
                text, extraction_method = _extract_page_text(page, settings)
                tables = _extract_tables(page) if settings.pdf_extract_tables else []
                formulas = _extract_formula_lines(text) if settings.pdf_extract_formulas else []
                if extraction_method == "ocr":
                    ocr_page_count += 1
                table_count += len(tables)
                formula_count += len(formulas)
                page_texts.append(
                    PageText(
                        page_number=index,
                        text=text,
                        extraction_method=extraction_method,
                        tables=tables,
                        formulas=formulas,
                    )
                )
                raw_parts.append(text)
                sections.extend(_find_section_candidates(index, text))
    except PdfPageLimitError:
        raise
    except Exception as exc:
        raise RuntimeError("PDF parsing failed. Please confirm the uploaded file is a readable PDF.") from exc

    return ParsedPaper(
        raw_text="\n\n".join(part for part in raw_parts if part),
        page_texts=page_texts,
        section_candidates=sections,
        page_count=len(page_texts),
        ocr_page_count=ocr_page_count,
        table_count=table_count,
        formula_count=formula_count,
    )


def _extract_page_text(page: Any, settings: Any) -> tuple[str, str]:
    global _ocr_unavailable_logged
    native_text = page.get_text("text").strip()
    visible_chars = len(re.sub(r"\s+", "", native_text))
    if not settings.pdf_ocr_enabled or visible_chars >= max(0, settings.pdf_ocr_min_chars):
        return native_text, "native"

    try:
        text_page = page.get_textpage_ocr(
            language=settings.pdf_ocr_language,
            dpi=max(72, settings.pdf_ocr_dpi),
            full=True,
        )
        ocr_text = page.get_text("text", textpage=text_page).strip()
        if len(re.sub(r"\s+", "", ocr_text)) > visible_chars:
            return ocr_text, "ocr"
    except Exception:
        if not _ocr_unavailable_logged:
            logger.warning("OCR unavailable for sparse PDF pages; keeping native text", exc_info=True)
            _ocr_unavailable_logged = True
    return native_text, "native"


def _extract_tables(page: Any) -> list[str]:
    if not hasattr(page, "find_tables"):
        return []
    try:
        finder = page.find_tables()
        extracted: list[str] = []
        for table in list(getattr(finder, "tables", []))[:_MAX_TABLES_PER_PAGE]:
            markdown = _table_to_markdown(table.extract())
            if markdown:
                extracted.append(markdown)
        return extracted
    except Exception:
        logger.debug("Table extraction failed for a PDF page", exc_info=True)
        return []


def _table_to_markdown(rows: list[list[Any]] | None) -> str:
    if not rows:
        return ""
    normalized_rows: list[list[str]] = []
    width = min(max((len(row or []) for row in rows), default=0), _MAX_TABLE_COLUMNS)
    if width == 0:
        return ""
    for row in rows[:_MAX_TABLE_ROWS]:
        cells = [_clean_table_cell(cell) for cell in (row or [])[:width]]
        cells.extend([""] * (width - len(cells)))
        normalized_rows.append(cells)
    if not any(any(cell for cell in row) for row in normalized_rows):
        return ""
    header = normalized_rows[0]
    separator = ["---"] * width
    body = normalized_rows[1:]
    return "\n".join(_markdown_row(row) for row in [header, separator, *body])


def _clean_table_cell(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("|", "\\|").split())[:500]


def _markdown_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def _extract_formula_lines(text: str, limit: int = 24) -> list[str]:
    formulas: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not _looks_like_formula(line) or line in seen:
            continue
        formulas.append(line)
        seen.add(line)
        if len(formulas) >= limit:
            break
    return formulas


def _looks_like_formula(line: str) -> bool:
    if not 4 <= len(line) <= 240:
        return False
    symbol_count = sum(char in _MATH_SYMBOLS for char in line)
    has_math_term = bool(_MATH_TERMS.search(line))
    has_equation_number = bool(_EQUATION_NUMBER.search(line))
    word_count = len(re.findall(r"[A-Za-z]{3,}", line))
    return (
        symbol_count >= 2
        or ("=" in line and (has_math_term or has_equation_number or word_count <= 8))
        or (has_math_term and symbol_count >= 1)
    )
