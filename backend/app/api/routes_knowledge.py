from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.database import get_connection
from app.schemas.knowledge import KnowledgePaper, KnowledgeSearchResult
from app.services.retrieval import search_knowledge_base

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
)


@router.get(
    "/search",
    response_model=list[KnowledgeSearchResult],
    summary="Search knowledge base",
    description="Semantic search across all analyzed papers using persistent embeddings.",
)
def search_knowledge(
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(10, ge=1, le=50, description="Maximum results"),
) -> list[KnowledgeSearchResult]:
    results = search_knowledge_base(q, top_k=top_k)
    if not results:
        return []

    output: list[KnowledgeSearchResult] = []
    for r in results:
        paper_id = r.paper_id or ""

        output.append(
            KnowledgeSearchResult(
                paper_id=paper_id,
                paper_title=r.paper_title,
                chunk_index=r.metadata.chunk_index,
                chunk_content=r.content,
                section_title=r.metadata.section_title,
                page_start=r.metadata.page_start,
                score=r.score,
            )
        )
    return output


@router.get(
    "/papers",
    response_model=list[KnowledgePaper],
    summary="List knowledge base papers",
    description="List all papers that have been indexed with embeddings.",
)
def list_knowledge_papers() -> list[KnowledgePaper]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.title, p.filename, p.created_at,
                   COUNT(pe.id) as chunk_count
            FROM papers p
            JOIN paper_embeddings pe ON p.id = pe.paper_id
            GROUP BY p.id
            ORDER BY p.created_at DESC
            """
        ).fetchall()
    return [
        KnowledgePaper(
            paper_id=row["id"],
            title=row["title"],
            filename=row["filename"],
            chunk_count=row["chunk_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
