from __future__ import annotations

from app.schemas.chunks import ChunkMetadata, PaperChunk, RetrievedChunk
from app.schemas.classification import PaperTypeClassification
from app.schemas.common import EvidenceRef, MissingItem
from app.schemas.experiments import DatasetInfo, ExperimentAnalysis, ExperimentMatrixItem
from app.schemas.metadata import PaperMetadata
from app.schemas.method import AlgorithmStep, MethodAnalysis, MethodModule
from app.schemas.reproduction import ChecklistItem, ReproductionPlan
from app.schemas.understanding import PaperUnderstanding, ReadingTask
from app.services.markdown_exporter import build_markdown_report
from app.services.paper_analysis import audit_reproduction_gaps, chunk_role, evidence_from_chunk


def test_section_role_detects_method_experiment_and_conclusion():
    method_chunk = PaperChunk(
        content="We introduce the model architecture and algorithm.",
        metadata=ChunkMetadata(chunk_index=0, page_start=2, page_end=2, section_title="3 Methodology"),
    )
    experiment_chunk = PaperChunk(
        content="We evaluate the method on three datasets.",
        metadata=ChunkMetadata(chunk_index=1, page_start=5, page_end=5, section_title="4 Experiments"),
    )
    conclusion_chunk = PaperChunk(
        content="Future work will address the limitation.",
        metadata=ChunkMetadata(chunk_index=2, page_start=8, page_end=8, section_title="Conclusion"),
    )

    assert chunk_role(method_chunk) == "method"
    assert chunk_role(experiment_chunk) == "experiment"
    assert chunk_role(conclusion_chunk) == "conclusion"


def test_evidence_ref_preserves_page_and_section():
    chunk = RetrievedChunk(
        content="We evaluate on ReproBench and report F1. The method improves the baseline.",
        metadata=ChunkMetadata(chunk_index=3, page_start=6, page_end=6, section_title="4 Evaluation"),
        score=4.0,
        matched_terms=["evaluate"],
    )

    evidence = evidence_from_chunk(chunk, "实验指标", keywords=["report"])

    assert evidence.page == "p.6"
    assert evidence.section == "4 Evaluation"
    assert "F1" in evidence.quote
    assert evidence.claim == "实验指标"


def test_audit_reproduction_gaps_classifies_missing_items():
    gaps = audit_reproduction_gaps(
        datasets=[],
        metrics=[],
        baselines=[],
        training_details=[],
        method_dependencies=[],
        evidence_text="The full model was trained on 8 A100 GPUs after preprocessing and filtering the data.",
    )
    categories = {gap.category for gap in gaps}

    assert {"dataset", "metric", "baseline", "hyperparameter", "implementation_detail"} <= categories
    assert "compute" in categories
    assert "preprocessing" in categories


def test_markdown_report_contains_audit_sections():
    evidence = EvidenceRef(claim="主实验", page="p.5", section="Experiments", quote="We evaluate on ReproBench.", role="experiment")
    missing = MissingItem(category="dataset", item="缺少数据下载地址", severity="high", suggested_action="核查附录。")
    report = build_markdown_report(
        metadata=PaperMetadata(title="Example Paper"),
        classification=PaperTypeClassification(
            domain="llm",
            paper_type="experimental",
            reproduction_mode="benchmark_evaluation",
            difficulty="medium",
            suitability_for_mvp="partial",
        ),
        understanding=PaperUnderstanding(
            background="背景",
            core_problem="问题",
            main_contributions=["贡献"],
            overall_idea="思路",
            conclusion="结论",
            reading_tasks=[ReadingTask(item="确认问题", status="confirmed", evidence=[evidence], next_action="继续核查贡献。")],
            evidence_refs=[evidence],
        ),
        method=MethodAnalysis(
            method_summary="方法",
            modules=[
                MethodModule(
                    name="core_method",
                    responsibility="核心方法",
                    inputs=["x"],
                    outputs=["y"],
                    interface_contract="x -> y",
                    evidence=[evidence],
                )
            ],
            algorithm_steps=[AlgorithmStep(step=1, name="run", description="运行核心方法", evidence=[evidence])],
            system_framework="框架",
            implementation_dependencies=["Python"],
            evidence_refs=[evidence],
        ),
        experiments=ExperimentAnalysis(
            datasets=[DatasetInfo(name="ReproBench", role="benchmark", evidence=[evidence])],
            metrics=["F1"],
            baselines=["baseline"],
            main_results=["result"],
            training_details=["1 epoch"],
            evaluation_protocol="protocol",
            reproduction_matrix=[
                ExperimentMatrixItem(
                    target="最小主实验",
                    dataset="ReproBench",
                    baseline="baseline",
                    metric="F1",
                    protocol="protocol",
                    reported_result="result",
                    reproducibility_status="partial",
                    evidence=[evidence],
                )
            ],
            evidence_refs=[evidence],
        ),
        reproduction=ReproductionPlan(
            audit_summary="可以做部分复现。",
            confidence="medium",
            recommended_first_experiment="先跑 ReproBench F1。",
            feasibility_summary="可部分复现。",
            feasibility_level="medium",
            minimum_reproduction_goal="最小目标",
            experiment_checklist=[ChecklistItem(item="跑通最小实验")],
            blocking_missing_items=[missing],
            acceptance_criteria=["输出 F1 并记录差距。"],
            evidence_refs=[evidence],
        ),
    )

    assert "## 0. 复现审计摘要" in report
    assert "### 证据地图" in report
    assert "### 实验复现矩阵" in report
    assert "### 验收标准" in report
