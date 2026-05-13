import logging

from app.agents.state import PaperAnalysisState
from app.core.database import utc_now
from app.schemas.report import MarkdownReport
from app.services.markdown_exporter import build_markdown_report

logger = logging.getLogger(__name__)


def generate_report_node(state: PaperAnalysisState) -> PaperAnalysisState:
    node_errors = state.get("node_errors") or []
    language = state.get("report_language", "en")

    try:
        content = build_markdown_report(
            metadata=state["metadata"],
            classification=state["classification"],
            understanding=state["understanding"],
            method=state["method_analysis"],
            experiments=state["experiment_analysis"],
            reproduction=state["reproduction_plan"],
            language=language,
        )
    except KeyError:
        logger.warning("Missing state for full report, generating partial report")
        content = _partial_report(state, language)

    if node_errors:
        content += _error_appendix(node_errors, language)

    metadata = state.get("metadata")
    title = metadata.title if metadata else "Analysis Report"
    report = MarkdownReport(title=title, content=content, created_at=utc_now())
    return {"markdown_report": report, "status": "report_generated"}


def _partial_report(state: PaperAnalysisState, language: str) -> str:
    metadata = state.get("metadata")
    if metadata:
        title = metadata.title
        authors = ", ".join(metadata.authors) if metadata.authors else "N/A"
        abstract = metadata.abstract or "N/A"
    else:
        title = "N/A"
        authors = "N/A"
        abstract = "N/A"

    if language == "en":
        return (
            f"# Partial Analysis Report\n\n"
            f"**Title**: {title}\n"
            f"**Authors**: {authors}\n"
            f"**Abstract**: {abstract}\n\n"
            f"---\n\n"
            f"Some analysis steps failed. See the error appendix below for details.\n"
        )
    return (
        f"# 部分分析报告\n\n"
        f"**标题**: {title}\n"
        f"**作者**: {authors}\n"
        f"**摘要**: {abstract}\n\n"
        f"---\n\n"
        f"部分分析步骤失败，详见下方错误附录。\n"
    )


def _error_appendix(errors: list[dict[str, str]], language: str) -> str:
    if language == "en":
        lines = ["\n\n---\n\n## Error Appendix\n\n"]
        lines.append("The following analysis steps failed:\n\n")
        for err in errors:
            lines.append(f"- **{err['node']}**: {err['error']}\n")
    else:
        lines = ["\n\n---\n\n## 错误附录\n\n"]
        lines.append("以下分析步骤失败：\n\n")
        for err in errors:
            lines.append(f"- **{err['node']}**: {err['error']}\n")
    return "".join(lines)
