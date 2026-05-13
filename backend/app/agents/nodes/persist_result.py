import logging
from pathlib import Path

from pydantic import BaseModel

from app.agents.state import PaperAnalysisState
from app.core.config import get_settings
from app.core.database import (
    replace_chunks,
    save_analysis_result,
    save_report,
    update_paper_title,
)
from app.schemas.report import PersistResult
from app.services.retrieval import embed_and_store

logger = logging.getLogger(__name__)


def persist_result_node(state: PaperAnalysisState) -> PaperAnalysisState:
    settings = get_settings()
    paper_id = state["paper_id"]
    run_id = state["run_id"]
    report = state["markdown_report"]

    settings.report_path.mkdir(parents=True, exist_ok=True)
    report_path = Path(settings.report_path) / f"{run_id}.md"
    report_path.write_text(report.content, encoding="utf-8")

    if state.get("chunked_paper"):
        chunks = state["chunked_paper"].chunks
        replace_chunks(paper_id, [chunk.model_dump() for chunk in chunks])
        embed_and_store(chunks, paper_id)

    metadata = state.get("metadata")
    if metadata:
        update_paper_title(paper_id, metadata.title)

    analysis_data = {}
    for key, field in [
        ("metadata", "metadata"),
        ("classification", "classification"),
        ("understanding", "understanding"),
        ("method_analysis", "method_analysis"),
        ("experiment_analysis", "experiment_analysis"),
        ("reproduction_plan", "reproduction_plan"),
    ]:
        value = state.get(field)
        if isinstance(value, BaseModel):
            analysis_data[key] = value.model_dump()

    if analysis_data:
        save_analysis_result(run_id, paper_id, analysis_data)

    title = report.title if report.title else "Analysis Report"
    save_report(run_id, paper_id, title, report.content, report_path)

    persist_result = PersistResult(
        paper_id=paper_id,
        run_id=run_id,
        status="completed",
        report_path=str(report_path),
    )
    return {"persist_result": persist_result, "status": "completed"}
