from __future__ import annotations

from pydantic import BaseModel


class KnowledgeSearchResult(BaseModel):
    paper_id: str
    paper_title: str | None = None
    chunk_index: int
    chunk_content: str
    section_title: str | None = None
    page_start: int
    score: float


class KnowledgePaper(BaseModel):
    paper_id: str
    title: str | None = None
    filename: str
    chunk_count: int
    created_at: str
