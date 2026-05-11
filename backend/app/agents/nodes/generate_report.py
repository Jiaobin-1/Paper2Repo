from app.agents.state import PaperAnalysisState
from app.core.database import utc_now
from app.schemas.report import MarkdownReport
from app.services.markdown_exporter import build_markdown_report


def generate_report_node(state: PaperAnalysisState) -> PaperAnalysisState:
    content = build_markdown_report(
        metadata=state["metadata"],
        classification=state["classification"],
        understanding=state["understanding"],
        method=state["method_analysis"],
        experiments=state["experiment_analysis"],
        reproduction=state["reproduction_plan"],
    )
    report = MarkdownReport(title=state["metadata"].title, content=content, created_at=utc_now())
    return {"markdown_report": report, "status": "report_generated"}
