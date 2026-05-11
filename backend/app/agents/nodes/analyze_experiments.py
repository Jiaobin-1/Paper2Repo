from __future__ import annotations

import re

from app.agents.state import PaperAnalysisState
from app.agents.prompts import ANALYZE_EXPERIMENTS_PROMPT, COMMON_SYSTEM_PROMPT
from app.agents.nodes.node_utils import context_block, evidence_sentence, extract_sentences, llm_or_fallback
from app.schemas.experiments import DatasetInfo, ExperimentAnalysis
from app.services.retrieval import retrieve_context


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
    patterns = [
        r"(?:dataset|datasets|benchmark|benchmarks)\s+(?:including|include|such as|on|:)?\s*([A-Z][A-Za-z0-9_\-]+(?:,\s*[A-Z][A-Za-z0-9_\-]+){0,6})",
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
    context = retrieve_context(
        chunks,
        query="experiment dataset baseline metric evaluation ablation result",
        section_hints=["experiment", "evaluation", "result", "ablation"],
        keywords=["dataset", "baseline", "metric", "evaluation", "ablation", "result"],
        top_k=8,
    )
    text = " ".join(item.content for item in context)
    metrics = _extract_metrics(text)
    dataset_names = _extract_dataset_names(text)
    datasets = [
        DatasetInfo(name=name, role="实验数据集/基准", notes=evidence_sentence(context, [name], "论文片段中出现该数据集名称。"))
        for name in dataset_names
    ]

    fallback = ExperimentAnalysis(
        datasets=datasets,
        metrics=metrics,
        baselines=extract_sentences(context, ["baseline", "compare", "state-of-the-art", "sota"], limit=5)
        or ["当前 PDF 片段未明确抽取到 baseline 名称。"],
        main_results=extract_sentences(context, ["outperform", "improve", "result", "achieve", "performance"], limit=5)
        or ["当前 PDF 片段未明确抽取到主要实验结果。"],
        ablation_studies=extract_sentences(context, ["ablation", "variant", "component", "remove"], limit=4)
        or ["当前 PDF 片段未明确抽取到消融实验。"],
        training_details=extract_sentences(context, ["train", "epoch", "batch", "learning rate", "optimizer", "hyperparameter"], limit=5)
        or ["当前 PDF 片段未明确抽取到训练细节。"],
        evaluation_protocol=evidence_sentence(
            context,
            ["evaluate", "evaluation", "metric", "test set", "benchmark"],
            "当前 PDF 片段未明确说明评价协议。",
        ),
    )
    experiments = llm_or_fallback(
        system_prompt=COMMON_SYSTEM_PROMPT,
        task_prompt=ANALYZE_EXPERIMENTS_PROMPT,
        schema_model=ExperimentAnalysis,
        fallback=fallback,
        context=context_block(context),
        extra=(
            f"Paper metadata: {state['metadata'].model_dump_json()}\n"
            f"Paper classification: {state['classification'].model_dump_json()}\n"
            f"Method analysis: {state['method_analysis'].model_dump_json()}"
        ),
    )
    return {"experiment_analysis": experiments, "status": "experiments_analyzed"}
