from __future__ import annotations

import re

from app.agents.nodes.node_utils import context_block, evidence_sentence, llm_or_fallback
from app.agents.prompts import ANALYZE_METHOD_PROMPT, system_prompt_for_language
from app.agents.state import PaperAnalysisState
from app.schemas.common import MissingItem
from app.schemas.method import AlgorithmStep, MethodAnalysis, MethodModule
from app.services.paper_analysis import collect_evidence, retrieve_analysis_context

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
                implementation_priority="must" if name in {"data_or_input_processing", "core_model_or_reasoning"} else "should",
                interface_contract="输入输出接口未在当前片段中完整给出，需要复现前补齐。",
                evidence=collect_evidence(context, sentence, keywords=keywords, limit=1),
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
            implementation_priority="must",
            interface_contract="方法核心输入输出需要从 Method/Algorithm 章节人工确认。",
            evidence=collect_evidence(context, "方法核心", keywords=["method", "approach", "framework"], limit=1),
        )
    ]


def analyze_method_node(state: PaperAnalysisState) -> PaperAnalysisState:
    chunks = state["chunked_paper"].chunks
    context = retrieve_analysis_context(chunks, "method", top_k=10)

    raw_method_text = "\n".join(item.content for item in context)
    framework = evidence_sentence(
        context,
        ["framework", "architecture", "pipeline", "approach", "method", "model"],
        "当前 PDF 片段未明确给出方法框架。",
    )
    formulas = _extract_formulas(raw_method_text)
    dependencies = sorted(
        set(
            ["Python"]
            + [dep for dep in ["PyTorch", "Transformers", "FAISS", "OpenAI-compatible API"] if re.search(dep, raw_method_text, re.IGNORECASE)]
        )
    )
    missing_items: list[MissingItem] = []
    if not formulas:
        missing_items.append(
            MissingItem(
                category="formula_or_pseudocode",
                item="未找到可直接实现的关键公式、伪代码或目标函数。",
                severity="medium",
                evidence_or_reason="方法上下文没有稳定抽取到公式/伪代码。",
                suggested_action="复现前核查 Method、Algorithm、Appendix 中的公式和伪代码。",
            )
        )
    if "待从论文方法部分确认" in " ".join(note for module in _fallback_modules(context) for note in module.inputs + module.outputs):
        missing_items.append(
            MissingItem(
                category="implementation_detail",
                item="模块输入输出接口不完整。",
                severity="medium",
                evidence_or_reason="当前片段只支持粗粒度模块识别，不能直接落代码接口。",
                suggested_action="为每个核心模块补一行输入、输出、shape/type 或文件格式。",
            )
        )
    fallback = MethodAnalysis(
        method_summary=framework,
        modules=_fallback_modules(context),
        key_formulas=formulas,
        algorithm_steps=[
            AlgorithmStep(
                step=1,
                name="Prepare inputs",
                description=evidence_sentence(context, ["input", "dataset", "preprocess", "representation"], "准备论文定义的输入和预处理流程。"),
                evidence=collect_evidence(context, "方法输入和预处理", keywords=["input", "dataset", "preprocess", "representation"], limit=1),
            ),
            AlgorithmStep(
                step=2,
                name="Run core method",
                description=evidence_sentence(context, ["method", "model", "framework", "algorithm"], "实现论文核心方法或推理流程。"),
                evidence=collect_evidence(context, "核心方法流程", keywords=["method", "model", "framework", "algorithm"], limit=1),
            ),
            AlgorithmStep(
                step=3,
                name="Produce outputs",
                description=evidence_sentence(context, ["output", "prediction", "generate", "score"], "输出论文任务对应的预测、生成结果或评分。"),
                evidence=collect_evidence(context, "方法输出", keywords=["output", "prediction", "generate", "score"], limit=1),
            ),
        ],
        system_framework=framework,
        implementation_dependencies=dependencies,
        implementation_interfaces=[
            "data_pipeline -> core_method: 论文定义的数据样本、特征或 prompt 表示。",
            "core_method -> evaluation: 预测、生成结果、排序分数或任务输出。",
        ],
        formula_or_pseudocode_gaps=["当前片段未抽取到关键公式或伪代码，需人工核查。"] if not formulas else [],
        evidence_refs=collect_evidence(
            context,
            "方法框架和核心模块",
            keywords=["framework", "architecture", "pipeline", "method", "model"],
            limit=3,
        ),
        missing_items=missing_items,
    )
    method, _used_llm = llm_or_fallback(
        system_prompt=system_prompt_for_language(state.get("report_language")),
        task_prompt=ANALYZE_METHOD_PROMPT,
        schema_model=MethodAnalysis,
        fallback=fallback,
        context=context_block(context),
        extra=(
            f"Paper metadata: {state['metadata'].model_dump_json()}\n"
            f"Paper understanding: {state['understanding'].model_dump_json()}"
        ),
        model_name=state.get("model_name"),
    )
    return {"method_analysis": method, "status": "method_analyzed"}
