from __future__ import annotations

from app.core.database import create_paper, init_db, replace_chunks, save_embeddings
from app.schemas.chunks import ChunkMetadata, PaperChunk
from app.services import retrieval
from app.services.retrieval import new_embedding_cache, retrieve_context, search_knowledge_base


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

    def test_reuses_chunk_embeddings_with_cache(self, monkeypatch):
        monkeypatch.setattr(retrieval, "_HAS_EMBEDDINGS", True)
        calls = {"chunks": 0}

        class FakeModel:
            def encode(self, texts, show_progress_bar=False):
                if len(texts) > 1:
                    calls["chunks"] += 1
                return retrieval.np.array([[1.0, 0.0] for _ in texts])

        monkeypatch.setattr(retrieval, "_get_embedding_model", lambda: FakeModel())
        chunks = [
            _make_chunk(0, "Transformer method.", section="Method"),
            _make_chunk(1, "Evaluation results.", section="Experiments"),
        ]
        cache = new_embedding_cache()
        retrieve_context(chunks, query="method", keywords=["method"], embedding_cache=cache)
        retrieve_context(chunks, query="results", keywords=["results"], embedding_cache=cache)
        assert calls["chunks"] == 1

    def test_knowledge_search_preserves_paper_id_for_same_chunk_index(self, isolated_settings, monkeypatch):
        init_db()
        monkeypatch.setattr(retrieval, "_HAS_EMBEDDINGS", True)

        class FakeModel:
            def encode(self, texts, show_progress_bar=False):
                return retrieval.np.array([[1.0, 0.0] for _ in texts])

        monkeypatch.setattr(retrieval, "_get_embedding_model", lambda: FakeModel())
        pdf_a = isolated_settings / "a.pdf"
        pdf_b = isolated_settings / "b.pdf"
        pdf_a.write_bytes(b"%PDF-1.4\n%%EOF")
        pdf_b.write_bytes(b"%PDF-1.4\n%%EOF")
        paper_a = create_paper("a.pdf", pdf_a, pdf_a.stat().st_size, title="Paper A")
        paper_b = create_paper("b.pdf", pdf_b, pdf_b.stat().st_size, title="Paper B")
        replace_chunks(paper_a["id"], [_make_chunk(0, "Unrelated paper A.", section="Method").model_dump()])
        replace_chunks(paper_b["id"], [_make_chunk(0, "Target paper B.", section="Method").model_dump()])
        save_embeddings(paper_a["id"], [(0, retrieval.np.array([0.0, 1.0], dtype="float32").tobytes())])
        save_embeddings(paper_b["id"], [(0, retrieval.np.array([1.0, 0.0], dtype="float32").tobytes())])

        results = search_knowledge_base("target", top_k=1)

        assert results[0].paper_id == paper_b["id"]
        assert results[0].paper_title == "Paper B"
