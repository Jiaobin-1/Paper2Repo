from typing import TypedDict

from app.schemas.chunks import ChunkedPaper
from app.schemas.classification import PaperTypeClassification
from app.schemas.experiments import ExperimentAnalysis
from app.schemas.metadata import PaperMetadata
from app.schemas.method import MethodAnalysis
from app.schemas.parsed import ParsedPaper
from app.schemas.report import MarkdownReport, PersistResult
from app.schemas.reproduction import ReproductionPlan
from app.schemas.understanding import PaperUnderstanding


class PaperAnalysisState(TypedDict, total=False):
    paper_id: str
    run_id: str
    pdf_path: str
    model_name: str
    report_language: str

    parsed_paper: ParsedPaper
    chunked_paper: ChunkedPaper
    metadata: PaperMetadata
    classification: PaperTypeClassification
    understanding: PaperUnderstanding
    method_analysis: MethodAnalysis
    experiment_analysis: ExperimentAnalysis
    reproduction_plan: ReproductionPlan
    markdown_report: MarkdownReport
    persist_result: PersistResult

    node_errors: list[dict[str, str]]
    status: str
    error_message: str | None
