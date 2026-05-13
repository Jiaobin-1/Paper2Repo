from __future__ import annotations

from app.schemas.parsed import PageText, ParsedPaper, SectionCandidate
from app.services.chunker import _estimate_tokens, _split_text, chunk_parsed_paper


def _make_parsed_paper(
    pages: list[tuple[int, str]],
    sections: list[SectionCandidate] | None = None,
) -> ParsedPaper:
    return ParsedPaper(
        raw_text="\n\n".join(text for _, text in pages),
        page_texts=[PageText(page_number=n, text=t) for n, t in pages],
        section_candidates=sections or [],
        page_count=len(pages),
    )


class TestSplitText:
    def test_short_text_returns_single_chunk(self):
        result = _split_text("hello world", max_chars=100)
        assert result == ["hello world"]

    def test_empty_text_returns_single_empty_chunk(self):
        result = _split_text("", max_chars=100)
        assert result == [""]

    def test_splits_on_paragraph_boundary(self):
        text = "A" * 1200 + "\n\n" + "B" * 1200
        result = _split_text(text, max_chars=1500)
        assert len(result) == 2
        assert result[0].startswith("A")
        assert result[1].startswith("B")

    def test_long_text_not_split_when_no_paragraph_breaks(self):
        text = "x" * 3000
        result = _split_text(text, max_chars=1000)
        assert len(result) == 1
        assert result[0] == text


class TestEstimateTokens:
    def test_empty_string_returns_zero(self):
        assert _estimate_tokens("") == 0

    def test_estimates_quarter_of_length(self):
        assert _estimate_tokens("abcdefgh") == 2

    def test_minimum_one_token(self):
        assert _estimate_tokens("ab") == 1


class TestChunkParsedPaper:
    def test_basic_chunking(self):
        parsed = _make_parsed_paper([(1, "Hello world."), (2, "Second page.")])
        result = chunk_parsed_paper(parsed, max_chars=2500)
        assert result.chunk_count == 2
        assert len(result.chunks) == 2

    def test_max_chars_enforcement_with_paragraphs(self):
        text = "A" * 900 + "\n\n" + "B" * 900 + "\n\n" + "C" * 900
        parsed = _make_parsed_paper([(1, text)])
        result = chunk_parsed_paper(parsed, max_chars=1000)
        assert result.chunk_count == 3
        for chunk in result.chunks:
            assert len(chunk.content) <= 1000

    def test_section_title_assignment(self):
        sections = [SectionCandidate(title="Introduction", page_number=1, level=1)]
        parsed = _make_parsed_paper([(1, "Some intro text.")], sections=sections)
        result = chunk_parsed_paper(parsed)
        assert result.chunks[0].metadata.section_title == "Introduction"

    def test_empty_pages_skipped(self):
        parsed = _make_parsed_paper([(1, ""), (2, "Content here.")])
        result = chunk_parsed_paper(parsed)
        assert result.chunk_count == 1
        assert result.chunks[0].metadata.page_start == 2

    def test_token_estimates_populated(self):
        parsed = _make_parsed_paper([(1, "Some text for token estimation.")])
        result = chunk_parsed_paper(parsed)
        assert result.chunks[0].metadata.token_estimate > 0

    def test_chunk_indices_sequential(self):
        parsed = _make_parsed_paper([(1, "A" * 3000), (2, "B" * 3000)])
        result = chunk_parsed_paper(parsed, max_chars=1500)
        for i, chunk in enumerate(result.chunks):
            assert chunk.metadata.chunk_index == i
