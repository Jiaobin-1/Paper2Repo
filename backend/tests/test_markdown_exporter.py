from __future__ import annotations

from app.schemas.classification import PaperTypeClassification
from app.schemas.common import EvidenceRef, MissingItem
from app.schemas.experiments import ExperimentAnalysis
from app.schemas.metadata import PaperMetadata
from app.schemas.method import MethodAnalysis
from app.schemas.reproduction import ReproductionPlan
from app.schemas.understanding import PaperUnderstanding
from app.services.markdown_exporter import build_markdown_report
from app.services.report_helpers import _cell


def _minimal_metadata(title: str = "Test Paper") -> PaperMetadata:
    return PaperMetadata(title=title, authors=["Author A"], abstract="An abstract.", keywords=["test"])


def _minimal_classification() -> PaperTypeClassification:
    return PaperTypeClassification(
        domain="llm",
        paper_type="experimental",
        reproduction_mode="inference_pipeline",
        difficulty="medium",
        suitability_for_mvp="good",
        reasons=["reason one"],
        required_resources=["GPU"],
        likely_blockers=["data access"],
    )


def _minimal_understanding() -> PaperUnderstanding:
    return PaperUnderstanding(
        background="Some background.",
        core_problem="The core problem.",
        main_contributions=["Contribution A"],
        overall_idea="The idea.",
        conclusion="The conclusion.",
        limitations=["Limitation A"],
        applicable_scenarios=["Scenario A"],
        key_assumptions=["Assumption A"],
        reading_tasks=[],
        evidence_refs=[],
        missing_items=[],
    )


def _minimal_method() -> MethodAnalysis:
    return MethodAnalysis(
        system_framework="Framework",
        method_summary="Summary.",
        modules=[],
        algorithm_steps=[],
        key_formulas=[],
        formula_or_pseudocode_gaps=[],
        implementation_interfaces=[],
        implementation_dependencies=[],
        evidence_refs=[],
        missing_items=[],
    )


def _minimal_experiments() -> ExperimentAnalysis:
    return ExperimentAnalysis(
        datasets=[],
        baselines=[],
        metrics=[],
        training_details=[],
        evaluation_protocol="Standard protocol.",
        main_results=["Result A"],
        ablation_studies=[],
        reproduction_matrix=[],
        evidence_refs=[],
        missing_items=[],
    )


def _minimal_reproduction() -> ReproductionPlan:
    return ReproductionPlan(
        feasibility_level="medium",
        feasibility_summary="Feasible.",
        minimum_reproduction_goal="Goal.",
        recommended_first_experiment="First exp.",
        reproduction_scope=["Scope A"],
        required_modules=[],
        dataset_plan=["Plan A"],
        evaluation_plan=["Eval A"],
        code_structure=[],
        implementation_steps=[],
        acceptance_criteria=["Criterion A"],
        risk_points=[],
        experiment_checklist=[],
        missing_information=[],
        suggested_simplifications=[],
        evidence_refs=[],
        blocking_missing_items=[],
        audit_summary="Audit.",
        confidence="medium",
    )


class TestBuildMarkdownReport:
    def test_zh_output_contains_chinese_headers(self):
        report = build_markdown_report(
            _minimal_metadata(), _minimal_classification(), _minimal_understanding(),
            _minimal_method(), _minimal_experiments(), _minimal_reproduction(), language="zh",
        )
        assert "## 0. 复现审计摘要" in report
        assert "## 1. 论文基本信息" in report

    def test_en_output_contains_english_headers(self):
        report = build_markdown_report(
            _minimal_metadata(), _minimal_classification(), _minimal_understanding(),
            _minimal_method(), _minimal_experiments(), _minimal_reproduction(), language="en",
        )
        assert "## 0. Reproduction Audit Summary" in report
        assert "## 1. Paper Metadata" in report

    def test_minimal_inputs_produce_valid_report(self):
        report = build_markdown_report(
            _minimal_metadata(), _minimal_classification(), _minimal_understanding(),
            _minimal_method(), _minimal_experiments(), _minimal_reproduction(),
        )
        assert isinstance(report, str)
        assert len(report) > 100

    def test_report_title_in_output(self):
        report = build_markdown_report(
            _minimal_metadata("My Great Paper"), _minimal_classification(), _minimal_understanding(),
            _minimal_method(), _minimal_experiments(), _minimal_reproduction(),
        )
        assert "My Great Paper" in report

    def test_evidence_table_formatting(self):
        understanding = _minimal_understanding()
        understanding.evidence_refs = [
            EvidenceRef(claim="Claim A", page="p.3", section="Sec", quote="Quote text", role="method"),
        ]
        report = build_markdown_report(
            _minimal_metadata(), _minimal_classification(), understanding,
            _minimal_method(), _minimal_experiments(), _minimal_reproduction(),
        )
        assert "Claim A" in report
        assert "Quote text" in report

    def test_missing_table_formatting(self):
        reproduction = _minimal_reproduction()
        reproduction.blocking_missing_items = [
            MissingItem(category="dataset", severity="high", item="Dataset X", suggested_action="Find it"),
        ]
        report = build_markdown_report(
            _minimal_metadata(), _minimal_classification(), _minimal_understanding(),
            _minimal_method(), _minimal_experiments(), reproduction,
        )
        assert "Dataset X" in report


class TestCell:
    def test_pipe_escaping(self):
        assert _cell("a|b") == "a\\|b"

    def test_whitespace_normalization(self):
        assert _cell("a  \n  b") == "a b"

    def test_empty_value_returns_empty_string(self):
        assert _cell("") == ""

    def test_none_value_returns_empty_string(self):
        assert _cell(None) == ""
