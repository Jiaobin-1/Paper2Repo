from pathlib import Path

from app.agents.state import PaperAnalysisState
from app.core.config import get_settings
from app.core.database import (
    replace_chunks,
    save_analysis_result,
    save_report,
    update_paper_title,
)
from app.schemas.report import PersistResult


def persist_result_node(state: PaperAnalysisState) -> PaperAnalysisState:
    settings = get_settings()
    paper_id = state["paper_id"]
    run_id = state["run_id"]
    metadata = state["metadata"]
    report = state["markdown_report"]

    settings.report_path.mkdir(parents=True, exist_ok=True)
    report_path = Path(settings.report_path) / f"{run_id}.md"
    report_path.write_text(report.content, encoding="utf-8")

    replace_chunks(paper_id, [chunk.model_dump() for chunk in state["chunked_paper"].chunks])
    update_paper_title(paper_id, metadata.title)
    save_analysis_result(
        run_id,
        paper_id,
        {
            "metadata": metadata.model_dump(),
            "classification": state["classification"].model_dump(),
            "understanding": state["understanding"].model_dump(),
            "method_analysis": state["method_analysis"].model_dump(),
            "experiment_analysis": state["experiment_analysis"].model_dump(),
            "reproduction_plan": state["reproduction_plan"].model_dump(),
        },
    )
    save_report(run_id, paper_id, report.title, report.content, report_path)

    persist_result = PersistResult(
        paper_id=paper_id,
        run_id=run_id,
        status="completed",
        report_path=str(report_path),
    )
    return {"persist_result": persist_result, "status": "completed"}
