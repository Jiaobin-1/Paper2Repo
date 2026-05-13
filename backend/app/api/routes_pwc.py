from __future__ import annotations

import urllib.parse
from typing import Any

from fastapi import APIRouter, HTTPException

from app.core.database import get_analysis_result, get_paper, get_run

router = APIRouter(
    prefix="/runs",
    tags=["papers-with-code"],
)


@router.get(
    "/{run_id}/pwc-links",
    summary="Get Papers With Code links",
    description="Generate search links for Papers With Code based on analysis results.",
)
def get_pwc_links(run_id: str) -> dict[str, Any]:
    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run["status"] != "completed":
        raise HTTPException(status_code=400, detail="Run is not completed.")

    paper = get_paper(run["paper_id"])
    analysis = get_analysis_result(run_id)

    paper_title = paper.get("title", "") if paper else ""
    metadata = analysis.get("metadata_json") if analysis else {}
    method = analysis.get("method_json") if analysis else {}
    understanding = analysis.get("understanding_json") if analysis else {}

    keywords = metadata.get("keywords", []) if metadata else []
    method_name = method.get("method_name", "") if method else ""
    contributions = understanding.get("main_contributions", []) if understanding else []

    links: list[dict[str, str]] = []

    if paper_title:
        links.append({
            "label": paper_title,
            "url": _pwc_search_url(paper_title),
            "type": "paper",
        })

    if method_name and method_name.lower() != paper_title.lower():
        links.append({
            "label": method_name,
            "url": _pwc_search_url(method_name),
            "type": "method",
        })

    for kw in keywords[:3]:
        if kw and kw.lower() != paper_title.lower():
            links.append({
                "label": kw,
                "url": _pwc_search_url(kw),
                "type": "keyword",
            })

    for contrib in contributions[:2]:
        if contrib and len(contrib) > 5:
            short = contrib[:80]
            links.append({
                "label": short,
                "url": _pwc_search_url(contrib),
                "type": "contribution",
            })

    return {"links": links}


def _pwc_search_url(query: str) -> str:
    encoded = urllib.parse.quote(query)
    return f"https://paperswithcode.com/search?q={encoded}"
