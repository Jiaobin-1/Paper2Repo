from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from app.services.pdf_parser import _extract_formula_lines, _extract_page_text, _table_to_markdown, parse_pdf

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_PDF = FIXTURES / "sample.pdf"


pytestmark = pytest.mark.skipif(
    not SAMPLE_PDF.exists(),
    reason="sample.pdf fixture not found",
)


class TestParsePdf:
    def test_returns_parsed_paper(self, isolated_settings):
        pytest.importorskip("fitz")
        dest = isolated_settings / "sample.pdf"
        shutil.copy(SAMPLE_PDF, dest)
        result = parse_pdf(dest)
        assert result.page_count >= 1
        assert result.raw_text
        assert len(result.page_texts) == result.page_count

    def test_page_texts_have_content(self, isolated_settings):
        pytest.importorskip("fitz")
        dest = isolated_settings / "sample.pdf"
        shutil.copy(SAMPLE_PDF, dest)
        result = parse_pdf(dest)
        for page in result.page_texts:
            assert page.page_number >= 1
            assert isinstance(page.text, str)

    def test_section_candidates_is_list(self, isolated_settings):
        pytest.importorskip("fitz")
        dest = isolated_settings / "sample.pdf"
        shutil.copy(SAMPLE_PDF, dest)
        result = parse_pdf(dest)
        assert isinstance(result.section_candidates, list)

    def test_file_not_found_raises(self, isolated_settings):
        pytest.importorskip("fitz")
        with pytest.raises(FileNotFoundError):
            parse_pdf("/nonexistent/path/to/paper.pdf")

    def test_rejects_pdf_over_page_limit(self, isolated_settings):
        fitz = pytest.importorskip("fitz")
        path = isolated_settings / "too-many-pages.pdf"
        with fitz.open() as document:
            document.new_page()
            document.new_page()
            document.save(path)

        with pytest.raises(RuntimeError, match="exceeding the configured limit of 1"):
            parse_pdf(path, max_pages=1)


def test_table_rows_are_normalized_to_markdown():
    markdown = _table_to_markdown([["Dataset", "F1"], ["Sample|Bench", 0.91]])

    assert "| Dataset | F1 |" in markdown
    assert "Sample\\|Bench" in markdown
    assert "| --- | --- |" in markdown


def test_formula_detection_keeps_equations_and_rejects_prose():
    formulas = _extract_formula_lines(
        "The model is effective on benchmarks.\nloss = -log p(y|x) (1)\nx = W h + b\n"
    )

    assert "loss = -log p(y|x) (1)" in formulas
    assert "x = W h + b" in formulas
    assert all("effective" not in formula for formula in formulas)


def test_sparse_page_uses_optional_ocr_when_it_improves_text():
    class Settings:
        pdf_ocr_enabled = True
        pdf_ocr_min_chars = 80
        pdf_ocr_language = "eng"
        pdf_ocr_dpi = 150

    class Page:
        def get_text(self, _kind, textpage=None):
            return "Recognized text from a scanned research paper." if textpage else ""

        def get_textpage_ocr(self, **_kwargs):
            return object()

    text, method = _extract_page_text(Page(), Settings())

    assert method == "ocr"
    assert "Recognized text" in text
