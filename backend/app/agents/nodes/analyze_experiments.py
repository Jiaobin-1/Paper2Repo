from __future__ import annotations

import re

from app.agents.nodes.node_utils import context_block, evidence_sentence, extract_sentences, llm_or_fallback
from app.agents.prompts import ANALYZE_EXPERIMENTS_PROMPT, system_prompt_for_language
from app.agents.state import PaperAnalysisState
from app.schemas.common import MissingItem
from app.schemas.experiments import DatasetInfo, ExperimentAnalysis, ExperimentMatrixItem
from app.services.paper_analysis import collect_evidence, retrieve_analysis_context

COMMON_METRICS = [
    "accuracy",
    "acc",
    "f1",
    "precision",
    "recall",
    "bleu",
    "rouge",
    "meteor",
    "mrr",
    "ndcg",
    "auc",
    "mae",
    "rmse",
    "perplexity",
    "win rate",
    "success rate",
]


def _extract_dataset_names(text: str) -> list[str]:
    candidates: set[str] = set()
    _ds_prefix = r"(?:dataset|datasets|benchmark|benchmarks)\s+(?:including|include|such as|on|:)?\s*"
    _ds_capture = r"([A-Z][A-Za-z0-9_\-]+(?:,\s*[A-Z][A-Za-z0-9_\-]+){0,6})"
    patterns = [
        _ds_prefix + _ds_capture,
        r"\b([A-Z][A-Za-z0-9_\-]*(?:Bench|QA|GLUE|Set|Net|Eval|Benchmarks?))\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            for item in re.split(r",|/| and ", match.group(1)):
                name = item.strip(" .;:()[]")
                if 2 < len(name) < 40:
                    candidates.add(name)
    return sorted(candidates)[:8]


def _extract_metrics(text: str) -> list[str]:
    lower = text.lower()
    metrics = []
    for metric in COMMON_METRICS:
        if metric in lower:
            metrics.append(metric.upper() if len(metric) <= 4 else metric)
    percent_metrics = re.findall(r"\b[A-Z][A-Za-z ]{1,24}(?:Rate|Score|Accuracy|F1)\b", text)
    metrics.extend(percent_metrics[:6])
    return sorted(set(metrics))


def analyze_experiments_node(state: PaperAnalysisState) -> PaperAnalysisState:
    chunks = state["chunked_paper"].chunks
    context = retrieve_analysis_context(chunks, "experiment", top_k=10, embedding_cache=state.get("retrieval_cache"))
    text = " ".join(item.content for item in context)
    metrics = _extract_metrics(text)
    dataset_names = _extract_dataset_names(text)
    datasets = [
        DatasetInfo(
            name=name,
            role="实验数据集/基准",
            notes=evidence_sentence(context, [name], "论文片段中出现该数据集名称。"),
            evidence=collect_evidence(context, f"数据集 {name}", keywords=[name], limit=1),
        )
        for name in dataset_names
    ]
    baselines = extract_sentences(context, ["baseline", "compare", "state-of-the-art", "sota"], limit=5)
    main_results = extract_sentences(context, ["outperform", "improve", "result", "achieve", "performance"], limit=5)
    ablations = extract_sentences(context, ["ablation", "variant", "component", "remove"], limit=4)
    training_details = extract_sentences(
        context, ["train", "epoch", "batch", "learning rate", "optimizer", "hyperparameter"], limit=5,
    )
    missing_items: list[MissingItem] = []
    if not datasets:
        missing_items.append(
            MissingItem(
                category="dataset",
                item="未找到明确数据集名称。",
                severity="high",
                evidence_or_reason="实验上下文没有稳定抽取到 dataset/benchmark 名称。",
                suggested_action="核查 Experiment/Evaluation 表格和 Appendix 的数据说明。",
            )
        )
    if not metrics:
        missing_items.append(
            MissingItem(
                category="metric",
                item="未找到明确评价指标。",
                severity="high",
                evidence_or_reason="实验片段未命中常见指标或表格指标名。",
                suggested_action="从实验表头或 evaluation protocol 中补齐指标定义。",
            )
        )
    if not baselines:
        missing_items.append(
            MissingItem(
                category="baseline",
                item="未找到明确 baseline。",
                severity="medium",
                evidence_or_reason="实验片段没有 baseline/compare/SOTA 等可对照句子。",
                suggested_action="核查主实验表格和相关工作中的比较方法。",
            )
        )
    if not training_details:
        missing_items.append(
            MissingItem(
                category="hyperparameter",
                item="未找到训练细节、超参数或随机种子。",
                severity="medium",
                evidence_or_reason="实验片段未命中 epoch/batch/optimizer/learning rate 等信号。",
                suggested_action="核查 Implementation Details 或 Appendix。",
            )
        )
    matrix = [
        ExperimentMatrixItem(
            target="最小主实验",
            dataset=", ".join(dataset.name for dataset in datasets[:3]) or "未找到",
            baseline=baselines[0] if baselines else "未找到",
            metric=", ".join(metrics[:3]) or "未找到",
            protocol=evidence_sentence(context, ["evaluate", "evaluation", "metric", "test set", "benchmark"], "未找到明确评价协议。"),
            reported_result=main_results[0] if main_results else "未找到",
            reproducibility_status="partial" if datasets and metrics else "blocked",
            missing_items=[item.item for item in missing_items],
            evidence=collect_evidence(context, "最小主实验证据", keywords=["dataset", "baseline", "metric", "result"], limit=3),
        )
    ]

    fallback = ExperimentAnalysis(
        datasets=datasets,
        metrics=metrics,
        baselines=baselines or ["当前 PDF 片段未明确抽取到 baseline 名称。"],
        main_results=main_results or ["当前 PDF 片段未明确抽取到主要实验结果。"],
        ablation_studies=ablations or ["当前 PDF 片段未明确抽取到消融实验。"],
        training_details=training_details or ["当前 PDF 片段未明确抽取到训练细节。"],
        evaluation_protocol=evidence_sentence(
            context,
            ["evaluate", "evaluation", "metric", "test set", "benchmark"],
            "当前 PDF 片段未明确说明评价协议。",
        ),
        reproduction_matrix=matrix,
        evidence_refs=collect_evidence(
            context,
            "实验设置、数据集、指标和结果",
            keywords=["dataset", "baseline", "metric", "evaluation", "result"],
            limit=4,
        ),
        missing_items=missing_items,
    )
    experiments, _used_llm = llm_or_fallback(
        system_prompt=system_prompt_for_language(state.get("report_language")),
        task_prompt=ANALYZE_EXPERIMENTS_PROMPT,
        schema_model=ExperimentAnalysis,
        fallback=fallback,
        context=context_block(context),
        extra=(
            f"Paper metadata: {state['metadata'].model_dump_json()}\n"
            f"Paper classification: {state['classification'].model_dump_json()}\n"
            f"Method analysis: {state['method_analysis'].model_dump_json()}"
        ),
        model_name=state.get("model_name"),
    )
    return {"experiment_analysis": experiments, "status": "experiments_analyzed"}
