from __future__ import annotations

from app.schemas.chunks import ChunkMetadata, PaperChunk
from app.services import retrieval
from app.services.retrieval import retrieve_context


def _make_chunk(index: int, content: str, page: int = 1, section: str | None = None) -> PaperChunk:
    return PaperChunk(
        content=content,
        metadata=ChunkMetadata(chunk_index=index, page_start=page, page_end=page, section_title=section),
    )


class TestKeywordFallback:
    def test_works_without_embeddings(self, monkeypatch):
        monkeypatch.setattr(retrieval, "_HAS_EMBEDDINGS", False)
        chunks = [
            _make_chunk(0, "The transformer model uses attention mechanisms.", section="Method"),
            _make_chunk(1, "We evaluate on ImageNet dataset.", section="Experiments"),
        ]
        results = retrieve_context(chunks, query="attention", keywords=["transformer"])
        assert len(results) >= 1
        assert any("transformer" in r.matched_terms for r in results)

    def test_section_hint_scoring(self, monkeypatch):
        monkeypatch.setattr(retrieval, "_HAS_EMBEDDINGS", False)
        chunks = [
            _make_chunk(0, "Some text.", section="Introduction"),
            _make_chunk(1, "Other text.", section="Methodology"),
        ]
        results = retrieve_context(chunks, section_hints=["methodology"])
        assert len(results) >= 1
        assert results[0].metadata.chunk_index == 1

    def test_returns_empty_when_no_match(self, monkeypatch):
        monkeypatch.setattr(retrieval, "_HAS_EMBEDDINGS", False)
        chunks = [_make_chunk(0, "Hello world.")]
        results = retrieve_context(chunks, query="xyznonexistent", keywords=["abc"])
        assert results == []


class TestVectorRetrieval:
    def test_blends_scores_when_embeddings_available(self, monkeypatch):
        monkeypatch.setattr(retrieval, "_HAS_EMBEDDINGS", True)

        def fake_embedding_scores(query, chunks):
            return [0.9, 0.1]

        monkeypatch.setattr(retrieval, "_embedding_scores", fake_embedding_scores)
        chunks = [
            _make_chunk(0, "Deep learning for NLP.", section="Method"),
            _make_chunk(1, "Unrelated content about cooking.", section="Other"),
        ]
        results = retrieve_context(chunks, query="deep learning NLP")
        assert len(results) >= 1

    def test_graceful_fallback_on_embedding_error(self, monkeypatch):
        monkeypatch.setattr(retrieval, "_HAS_EMBEDDINGS", True)

        def failing_scores(query, chunks):
            raise RuntimeError("model load failed")

        monkeypatch.setattr(retrieval, "_embedding_scores", failing_scores)
        chunks = [
            _make_chunk(0, "The transformer model.", section="Method"),
        ]
        results = retrieve_context(chunks, query="transformer", keywords=["transformer"])
        assert len(results) >= 1
