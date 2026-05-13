from __future__ import annotations

from app.services.pdf_exporter import (
    _clean_inline,
    _markdown_to_blocks,
    build_report_pdf,
)


class TestBuildReportPdf:
    def test_output_starts_with_pdf_magic(self):
        result = build_report_pdf("Test Title", "# Hello\n\nSome content.")
        assert result[:5] == b"%PDF-"

    def test_output_is_nonempty_bytes(self):
        result = build_report_pdf("Title", "# Heading\n\nBody text.")
        assert isinstance(result, bytes)
        assert len(result) > 100


class TestMarkdownToBlocks:
    def test_heading_detection(self):
        blocks = _markdown_to_blocks("## Hello World")
        assert len(blocks) == 1
        assert blocks[0].kind == "heading"
        assert blocks[0].text == "Hello World"
        assert blocks[0].level == 2

    def test_h1_detection(self):
        blocks = _markdown_to_blocks("# Title")
        assert blocks[0].level == 1

    def test_bullet_detection(self):
        blocks = _markdown_to_blocks("- item one")
        assert len(blocks) == 1
        assert blocks[0].kind == "bullet"
        assert blocks[0].text == "item one"

    def test_ordered_list_detection(self):
        blocks = _markdown_to_blocks("1. first step")
        assert blocks[0].kind == "bullet"
        assert "1." in blocks[0].text

    def test_code_block_detection(self):
        md = "```python\ncode here\n```"
        blocks = _markdown_to_blocks(md)
        assert len(blocks) == 1
        assert blocks[0].kind == "code"
        assert "code here" in blocks[0].text

    def test_spacer_for_blank_line(self):
        blocks = _markdown_to_blocks("line1\n\nline2")
        kinds = [b.kind for b in blocks]
        assert "spacer" in kinds

    def test_page_break_for_separator(self):
        blocks = _markdown_to_blocks("---")
        assert blocks[0].kind == "page_break"

    def test_quote_detection(self):
        blocks = _markdown_to_blocks("> quoted text")
        assert blocks[0].kind == "quote"
        assert blocks[0].text == "quoted text"

    def test_body_text_detection(self):
        blocks = _markdown_to_blocks("Just a paragraph.")
        assert blocks[0].kind == "body"

    def test_checkbox_bullet(self):
        blocks = _markdown_to_blocks("- [ ] check this")
        assert blocks[0].kind == "bullet"


class TestCleanInline:
    def test_removes_markdown_links(self):
        result = _clean_inline("[text](https://example.com)")
        assert "text" in result
        assert "https://example.com" in result

    def test_removes_bold_markers(self):
        result = _clean_inline("**bold**")
        assert result == "bold"

    def test_removes_italic_markers(self):
        result = _clean_inline("*italic*")
        assert result == "italic"

    def test_removes_backticks(self):
        result = _clean_inline("`code`")
        assert result == "code"

    def test_collapses_whitespace(self):
        result = _clean_inline("a  b")
        assert result == "a b"
