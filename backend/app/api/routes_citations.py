from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_citations_for_run, get_paper, get_run, list_runs

router = APIRouter(tags=["citations"])


@router.get(
    "/runs/{run_id}/citations",
    summary="Get citations for a run",
    description="Retrieve parsed citation references from an analysis run.",
)
def get_run_citations(run_id: str) -> dict:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    citations = get_citations_for_run(run_id)
    return {"run_id": run_id, "paper_id": run["paper_id"], "citations": citations}


@router.get(
    "/citations/network",
    summary="Citation network across papers",
    description="Return citation edges showing which analyzed papers cite each other, matched by title similarity.",
)
def get_citation_network(
    paper_ids: str = Query(..., description="Comma-separated paper IDs"),
) -> dict:
    ids = [pid.strip() for pid in paper_ids.split(",") if pid.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No paper IDs provided.")

    all_citations: dict[str, list[dict]] = {}
    for pid in ids:
        runs = list_runs(paper_id=pid, limit=20)
        if not runs:
            continue
        completed_run = next((run for run in runs if run.get("status") == "completed"), None)
        if not completed_run:
            continue
        run_id = completed_run["id"]
        citations = get_citations_for_run(run_id)
        if citations:
            all_citations[pid] = citations

    paper_titles: dict[str, str] = {}
    for pid in ids:
        paper = get_paper(pid)
        if paper and paper.get("title"):
            paper_titles[pid] = paper["title"].lower().strip()

    edges: list[dict] = []
    for source_pid, citations in all_citations.items():
        source_title = paper_titles.get(source_pid, "")
        if not source_title:
            continue
        for cite in citations:
            cite_title = (cite.get("title") or "").lower().strip()
            if not cite_title:
                continue
            for target_pid, target_title in paper_titles.items():
                if target_pid == source_pid:
                    continue
                similarity = _title_similarity(cite_title, target_title)
                if similarity > 0.6:
                    edges.append({
                        "source_paper_id": source_pid,
                        "target_paper_id": target_pid,
                        "source_title": paper_titles.get(source_pid, ""),
                        "target_title": paper_titles.get(target_pid, ""),
                        "cited_title": cite.get("title", ""),
                        "similarity": round(similarity, 3),
                    })

    return {"edges": edges}


def _title_similarity(a: str, b: str) -> float:
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)
