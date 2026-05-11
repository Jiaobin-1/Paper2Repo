from __future__ import annotations

import re

from app.agents.state import PaperAnalysisState
from app.agents.prompts import ANALYZE_METHOD_PROMPT, COMMON_SYSTEM_PROMPT
from app.agents.nodes.node_utils import context_block, evidence_sentence, extract_sentences, llm_or_fallback
from app.schemas.method import AlgorithmStep, MethodAnalysis, MethodModule
from app.services.retrieval import retrieve_context


MODULE_KEYWORDS = [
    ("data_or_input_processing", ["input", "preprocess", "representation", "embedding", "retrieve"]),
    ("core_model_or_reasoning", ["model", "network", "transformer", "agent", "reasoning", "generator"]),
    ("training_or_optimization", ["train", "loss", "optimize", "fine-tune", "learning"]),
    ("evaluation_or_output", ["output", "predict", "generate", "evaluate", "score"]),
]


def _extract_formulas(text: str) -> list[str]:
    formulas: list[str] = []
    for line in text.splitlines():
        normalized = " ".join(line.split())
        if 8 <= len(normalized) <= 180 and any(symbol in normalized for symbol in ["=", "∑", "\\sum", "\\mathcal", "argmax", "arg min"]):
            formulas.append(normalized)
        if len(formulas) >= 6:
            break
    return formulas


def _fallback_modules(context) -> list[MethodModule]:
    modules: list[MethodModule] = []
    for name, keywords in MODULE_KEYWORDS:
        sentence = evidence_sentence(context, keywords, "")
        if not sentence:
            continue
        modules.append(
            MethodModule(
                name=name,
                responsibility=sentence,
                inputs=["待从论文方法部分确认"],
                outputs=["待从论文方法部分确认"],
                implementation_notes=["该模块来自方法相关片段的关键词抽取，后续应根据原文细化接口。"],
            )
        )
    if modules:
        return modules
    return [
        MethodModule(
            name="method_core",
            responsibility=evidence_sentence(context, ["method", "approach", "framework"], "当前 PDF 片段未明确抽取到方法模块。"),
            inputs=["paper-defined inputs"],
            outputs=["paper-defined outputs"],
            implementation_notes=["需要人工核查论文方法章节中的模块边界。"],
        )
    ]


def analyze_method_node(state: PaperAnalysisState) -> PaperAnalysisState:
    chunks = state["chunked_paper"].chunks
    context = retrieve_context(
        chunks,
        query="method approach model algorithm framework module",
        section_hints=["method", "methodology", "approach", "model", "algorithm"],
        keywords=["method", "approach", "algorithm", "framework", "module", "training", "inference"],
        top_k=8,
    )

    raw_method_text = "\n".join(item.content for item in context)
    framework = evidence_sentence(
        context,
        ["framework", "architecture", "pipeline", "approach", "method", "model"],
        "当前 PDF 片段未明确给出方法框架。",
    )
    fallback = MethodAnalysis(
        method_summary=framework,
        modules=_fallback_modules(context),
        key_formulas=_extract_formulas(raw_method_text),
        algorithm_steps=[
            AlgorithmStep(
                step=1,
                name="Prepare inputs",
                description=evidence_sentence(context, ["input", "dataset", "preprocess", "representation"], "准备论文定义的输入和预处理流程。"),
            ),
            AlgorithmStep(
                step=2,
                name="Run core method",
                description=evidence_sentence(context, ["method", "model", "framework", "algorithm"], "实现论文核心方法或推理流程。"),
            ),
            AlgorithmStep(
                step=3,
                name="Produce outputs",
                description=evidence_sentence(context, ["output", "prediction", "generate", "score"], "输出论文任务对应的预测、生成结果或评分。"),
            ),
        ],
        system_framework=framework,
        implementation_dependencies=sorted(
            set(
                ["Python"]
                + [dep for dep in ["PyTorch", "Transformers", "FAISS", "OpenAI-compatible API"] if re.search(dep, raw_method_text, re.IGNORECASE)]
            )
        ),
    )
    method = llm_or_fallback(
        system_prompt=COMMON_SYSTEM_PROMPT,
        task_prompt=ANALYZE_METHOD_PROMPT,
        schema_model=MethodAnalysis,
        fallback=fallback,
        context=context_block(context),
        extra=(
            f"Paper metadata: {state['metadata'].model_dump_json()}\n"
            f"Paper understanding: {state['understanding'].model_dump_json()}"
        ),
    )
    return {"method_analysis": method, "status": "method_analyzed"}
