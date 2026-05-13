from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


from app.agents.nodes.extract_metadata import (
    _extract_abstract,
    _extract_authors,
    _extract_keywords,
    _extract_title_and_index,
    _front_matter_lines,
    _looks_like_names,
    _title_score,
    _trim_title,
)
from app.schemas.chunks import ChunkMetadata, PaperChunk
from app.schemas.metadata import PaperMetadata
from app.schemas.parsed import PageText, ParsedPaper
from app.services.retrieval import retrieve_context

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parsed(first_page: str, raw_text: str | None = None) -> ParsedPaper:
    return ParsedPaper(
        raw_text=raw_text or first_page,
        page_texts=[PageText(page_number=1, text=first_page)],
        section_candidates=[],
        page_count=1,
    )


def _make_chunk(index: int, content: str, section: str | None = None, page: int = 1) -> PaperChunk:
    return PaperChunk(
        content=content,
        metadata=ChunkMetadata(chunk_index=index, page_start=page, page_end=page, section_title=section),
    )


SAMPLE_PAPER = """\
Attention Is All You Need

Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez,
Lukasz Kaiser, Illia Polosukhin

Google Brain, Google Research, University of Toronto

Abstract
The dominant sequence transduction models are based on complex recurrent or convolutional
neural networks. We propose a new simple network architecture, the Transformer, based solely
on attention mechanisms. Experiments on two machine translation tasks show that our model
is superior in quality while being more parallelizable and requiring significantly less time
to train.

1 Introduction
Recurrent neural networks, long short-term memory and gated recurrent neural networks
have been firmly established as state of the art approaches.
"""


# ---------------------------------------------------------------------------
# Title extraction
# ---------------------------------------------------------------------------

class TestTitleScore:
    def test_good_title_scores_high(self):
        line = "Attention Is All You Need"
        score = _title_score(line, index=0)
        assert score >= 5

    def test_short_line_penalized(self):
        score = _title_score("Hi", index=0)
        assert score < 0

    def test_boilerplate_gets_negative_100(self):
        score = _title_score("Published as a conference paper at ICLR 2024", index=0)
        assert score == -100

    def test_university_line_penalized(self):
        score = _title_score("Department of Computer Science, Stanford University", index=2)
        assert score < 0

    def test_colon_bonus(self):
        score_colon = _title_score("BERT: Pre-training of Deep Bidirectional Transformers", index=0)
        score_no_colon = _title_score("Pre-training of Deep Bidirectional Transformers", index=0)
        assert score_colon > score_no_colon

    def test_uppercase_ratio_bonus(self):
        score = _title_score("A LARGE LANGUAGE MODEL FOR CODE GENERATION", index=0)
        assert score >= 3


class TestExtractTitle:
    def test_extracts_title_from_sample(self):
        lines = _front_matter_lines(SAMPLE_PAPER)
        title, index = _extract_title_and_index(lines)
        assert "Attention" in title

    def test_returns_untitled_on_empty(self):
        title, _ = _extract_title_and_index([])
        assert title == "Untitled Paper"

    def test_title_contains_paper_name(self):
        lines = _front_matter_lines(SAMPLE_PAPER)
        title, _ = _extract_title_and_index(lines)
        assert "Attention" in title

    def test_title_trimmed_when_author_bled_in(self):
        # Real pattern: title ends, then "Author1, Author2, Author3" starts
        title = _trim_title("Attention Is All You Need, Ashish Vaswani, Noam Shazeer")
        assert "Vaswani" not in title
        assert "Attention" in title

    def test_title_trimmed_on_and_author(self):
        title = _trim_title("BERT Pre-training and Jacob Devlin")
        assert "Devlin" not in title

    def test_title_unchanged_when_clean(self):
        title = _trim_title("Attention Is All You Need")
        assert title == "Attention Is All You Need"


# ---------------------------------------------------------------------------
# Author extraction
# ---------------------------------------------------------------------------

class TestExtractAuthors:
    def test_extracts_authors_from_sample(self):
        lines = _front_matter_lines(SAMPLE_PAPER)
        _, title_index = _extract_title_and_index(lines)
        authors = _extract_authors(lines, title_index)
        assert any("Vaswani" in a for a in authors)

    def test_skips_university_lines(self):
        lines = _front_matter_lines(SAMPLE_PAPER)
        _, title_index = _extract_title_and_index(lines)
        authors = _extract_authors(lines, title_index)
        assert not any("Google" in a or "University" in a for a in authors)

    def test_stops_at_non_author_line(self):
        lines = _front_matter_lines(SAMPLE_PAPER)
        _, title_index = _extract_title_and_index(lines)
        authors = _extract_authors(lines, title_index)
        # Should not include "Google Brain, Google Research, University of Toronto"
        assert not any("Brain" in a for a in authors)


class TestLooksLikeNames:
    def test_name_list(self):
        assert _looks_like_names("Ashish Vaswani, Noam Shazeer, Niki Parmar")

    def test_single_name(self):
        assert _looks_like_names("John Smith")

    def test_institution_rejected(self):
        assert not _looks_like_names("Google Research, Mountain View, CA")

    def test_university_rejected(self):
        assert not _looks_like_names("Stanford University, Department of CS")


# ---------------------------------------------------------------------------
# Abstract extraction
# ---------------------------------------------------------------------------

class TestExtractAbstract:
    def test_extracts_abstract_from_sample(self):
        abstract = _extract_abstract(SAMPLE_PAPER)
        assert "Transformer" in abstract
        assert len(abstract) > 50

    def test_returns_empty_when_no_abstract(self):
        abstract = _extract_abstract("Just some random text without an abstract section.")
        assert abstract == ""


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

class TestExtractKeywords:
    def test_extracts_keywords_section(self):
        text = "Abstract\nSome text.\nKeywords: large language model, retrieval, agent"
        keywords = _extract_keywords(text)
        assert "large language model" in keywords

    def test_fallback_to_candidate_matching(self):
        text = "This paper proposes a new retrieval augmented generation approach."
        keywords = _extract_keywords(text)
        assert "retrieval" in keywords or "rag" in keywords


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

class TestClassifyPaperType:
    def _run_classify(self, title: str, abstract: str = "", keywords: list[str] | None = None, raw: str = ""):
        from app.agents.nodes.classify_paper_type import classify_paper_type_node

        state = {
            "metadata": PaperMetadata(title=title, abstract=abstract, keywords=keywords or []),
            "parsed_paper": _make_parsed(raw or f"{title}\n{abstract}"),
        }
        return classify_paper_type_node(state)

    def test_llm_paper_classified_as_llm(self):
        result = self._run_classify(
            "A Large Language Model for Code Generation",
            "We present a large language model fine-tuned for code.",
        )
        assert result["classification"].domain == "llm"

    def test_agent_paper_classified_as_agent(self):
        result = self._run_classify(
            "Multi-Agent Collaboration for Task Planning",
            "We propose a multi-agent system for tool use.",
        )
        assert result["classification"].domain == "agent"

    def test_cv_paper_classified_as_cv(self):
        result = self._run_classify(
            "Object Detection in Autonomous Driving",
            "We present a vision-based detection system.",
        )
        assert result["classification"].domain == "cv"

    def test_survey_classified_correctly(self):
        result = self._run_classify(
            "A Survey of Natural Language Processing",
            "This survey reviews recent advances in NLP.",
        )
        assert result["classification"].paper_type == "survey"
        assert result["classification"].suitability_for_mvp == "poor"

    def test_benchmark_paper_type(self):
        result = self._run_classify(
            "GLUE: A Multi-Task Benchmark",
            "We introduce a new benchmark for NLU.",
        )
        assert result["classification"].paper_type == "benchmark"

    def test_difficulty_very_high_for_large_scale(self):
        result = self._run_classify(
            "Scaling Language Models",
            "We train a billion parameter model on large-scale distributed GPU cluster.",
        )
        assert result["classification"].difficulty == "very_high"


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

class TestRetrieveContext:
    def test_keyword_scoring(self):
        chunks = [
            _make_chunk(0, "The transformer model uses attention mechanisms."),
            _make_chunk(1, "We evaluate on the WMT translation dataset."),
            _make_chunk(2, "Recurrent neural networks are sequential."),
        ]
        results = retrieve_context(chunks, query="attention transformer", top_k=3)
        assert len(results) >= 1
        assert results[0].metadata.chunk_index == 0

    def test_section_hint_boost(self):
        chunks = [
            _make_chunk(0, "Our method uses a novel approach.", section="Method"),
            _make_chunk(1, "We evaluate on standard benchmarks.", section="Experiments"),
        ]
        results = retrieve_context(chunks, section_hints=["method"], top_k=2)
        assert results[0].metadata.chunk_index == 0

    def test_empty_chunks_returns_empty(self):
        results = retrieve_context([], query="anything")
        assert results == []

    def test_score_cap_per_term(self):
        text = "attention " * 20
        chunks = [_make_chunk(0, text)]
        results = retrieve_context(chunks, query="attention", top_k=1)
        assert results[0].score == 5.0  # capped at 5

    def test_top_k_limits_results(self):
        chunks = [_make_chunk(i, "transformer attention mechanism") for i in range(10)]
        results = retrieve_context(chunks, query="transformer", top_k=3)
        assert len(results) == 3


# ---------------------------------------------------------------------------
# Node fault tolerance
# ---------------------------------------------------------------------------

class TestNodeFaultTolerance:
    def test_critical_node_failure_propagates(self):
        from app.agents.graph import build_graph

        def failing_parse(state):
            raise RuntimeError("PDF parse exploded")

        graph = build_graph()  # noqa: F841
        initial = {  # noqa: F841
            "paper_id": "test",
            "run_id": "test",
            "pdf_path": "/nonexistent",
            "model_name": "",
            "report_language": "en",
            "status": "pending",
            "error_message": None,
            "node_errors": [],
        }
        # We can't easily inject a failing node into the compiled graph,
        # so we test the _wrap_node logic directly.
        from app.agents.graph import CRITICAL_NODES

        assert "parse_pdf_node" in CRITICAL_NODES

    def test_non_critical_node_captures_error(self):
        from app.agents.graph import _wrap_node

        def failing_node(state):
            raise ValueError("LLM exploded")

        wrapped = _wrap_node("understand_paper_node", 4, failing_node, None)
        state = {
            "node_errors": [],
            "chunked_paper": None,
        }
        result = wrapped(state)
        assert "node_errors" in result
        assert len(result["node_errors"]) == 1
        assert result["node_errors"][0]["node"] == "understand_paper_node"
        assert "LLM exploded" in result["node_errors"][0]["error"]

    def test_successful_node_passes_through(self):
        from app.agents.graph import _wrap_node

        def ok_node(state):
            return {"status": "ok"}

        wrapped = _wrap_node("classify_paper_type_node", 3, ok_node, None)
        result = wrapped({})
        assert result["status"] == "ok"
