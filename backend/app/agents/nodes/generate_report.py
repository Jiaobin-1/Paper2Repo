import logging

from app.agents.state import PaperAnalysisState
from app.core.database import utc_now
from app.schemas.report import MarkdownReport
from app.services.reports.markdown import build_markdown_report

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

    parsed = state.get("parsed_paper")
    if parsed:
        content += _extraction_appendix(
            parsed.page_count,
            parsed.ocr_page_count,
            parsed.table_count,
            parsed.formula_count,
            language,
        )

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


def _extraction_appendix(
    page_count: int,
    ocr_page_count: int,
    table_count: int,
    formula_count: int,
    language: str,
) -> str:
    if language == "en":
        return (
            "\n\n---\n\n## Document Extraction Summary\n\n"
            f"- Pages parsed: {page_count}\n"
            f"- Pages using OCR: {ocr_page_count}\n"
            f"- Tables added to retrieval context: {table_count}\n"
            f"- Formula-like lines added to retrieval context: {formula_count}\n"
        )
    return (
        "\n\n---\n\n## 文档提取摘要\n\n"
        f"- 已解析页数：{page_count}\n"
        f"- 使用 OCR 的页数：{ocr_page_count}\n"
        f"- 加入检索上下文的表格数：{table_count}\n"
        f"- 加入检索上下文的公式行数：{formula_count}\n"
    )
