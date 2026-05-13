from app.agents.nodes.node_utils import context_block, evidence_sentence, extract_sentences, llm_or_fallback
from app.agents.prompts import UNDERSTAND_PAPER_PROMPT, system_prompt_for_language
from app.agents.state import PaperAnalysisState
from app.schemas.common import MissingItem
from app.schemas.understanding import PaperUnderstanding, ReadingTask
from app.services.paper_analysis import collect_evidence, retrieve_analysis_context


def understand_paper_node(state: PaperAnalysisState) -> PaperAnalysisState:
    chunks = state["chunked_paper"].chunks
    context = retrieve_analysis_context(chunks, "understanding", top_k=10)
    metadata = state["metadata"]

    contribution_sentences = extract_sentences(
        context,
        ["contribution", "we propose", "we present", "we introduce", "our method", "novel"],
        limit=4,
    )
    limitation_sentences = extract_sentences(context, ["limitation", "future work", "fail", "cannot", "however"], limit=3)
    evidence_refs = (
        collect_evidence(context, "研究问题/动机", keywords=["problem", "challenge", "motivation"], limit=1)
        + collect_evidence(context, "主要贡献", keywords=["contribution", "propose", "present", "introduce"], limit=2)
        + collect_evidence(context, "结论或效果", keywords=["conclusion", "result", "outperform", "effective"], limit=1)
    )
    missing_items: list[MissingItem] = []
    if not contribution_sentences:
        missing_items.append(
            MissingItem(
                category="contribution_evidence",
                item="未找到明确贡献列表或贡献证据。",
                severity="medium",
                evidence_or_reason="摘要/引言/结论片段未稳定命中 contribution/propose 等信号。",
                suggested_action="人工核查 Introduction 末尾和 Conclusion 中的贡献表述。",
            )
        )
    if not limitation_sentences:
        missing_items.append(
            MissingItem(
                category="limitation",
                item="未找到明确局限性或失败场景。",
                severity="low",
                evidence_or_reason="当前上下文没有 limitation/future work/fail 等句子。",
                suggested_action="核查 Discussion、Limitations、Appendix 或实验分析中的负结果。",
            )
        )
    fallback = PaperUnderstanding(
        background=metadata.abstract
        or evidence_sentence(context, ["background", "recent", "existing", "challenge"], "当前 PDF 片段未明确提取到研究背景。"),
        core_problem=evidence_sentence(
            context,
            ["problem", "challenge", "aim", "goal", "objective", "address"],
            "当前 PDF 片段未明确提取到核心问题。",
        ),
        main_contributions=contribution_sentences
        or extract_sentences(context, ["propose", "present", "introduce", "improve"], limit=3)
        or ["当前 PDF 片段未明确列出主要贡献，需要后续人工确认。"],
        overall_idea=evidence_sentence(
            context,
            ["method", "approach", "framework", "model", "pipeline"],
            "当前 PDF 片段未明确提取到整体方法思路。",
        ),
        conclusion=evidence_sentence(
            context,
            ["conclusion", "result", "outperform", "effective", "achieve"],
            "当前 PDF 片段未明确提取到论文结论。",
        ),
        limitations=limitation_sentences or ["当前 PDF 片段未明确说明局限性；复现时需重点核查数据、算力和实现细节。"],
        applicable_scenarios=[
            item
            for item in [state["classification"].domain, *metadata.keywords[:4]]
            if item and item != "other"
        ],
        key_assumptions=[
            "论文核心问题是否能从摘要/引言中被清楚定位。",
            "主要贡献是否有方法或实验章节证据支撑。",
            "论文结论是否依赖特定数据集、算力或实验设置。",
        ],
        reading_tasks=[
            ReadingTask(
                item="确认论文要解决的核心问题和动机。",
                status="confirmed" if evidence_refs else "unclear",
                evidence=collect_evidence(context, "核心问题", keywords=["problem", "challenge", "aim", "goal"], limit=1),
                next_action="若证据不足，优先阅读 Abstract 和 Introduction 前两页。",
            ),
            ReadingTask(
                item="确认主要贡献是否有原文证据。",
                status="confirmed" if contribution_sentences else "missing",
                evidence=collect_evidence(context, "主要贡献", keywords=["contribution", "propose", "present", "introduce"], limit=2),
                next_action="把贡献逐条映射到方法模块或实验结果。",
            ),
            ReadingTask(
                item="确认局限性、失败场景和适用边界。",
                status="confirmed" if limitation_sentences else "missing",
                evidence=collect_evidence(context, "局限性", keywords=["limitation", "future work", "fail", "however"], limit=1),
                next_action="若论文未写明，复现报告中保留为风险项。",
            ),
        ],
        evidence_refs=evidence_refs,
        missing_items=missing_items,
    )
    understanding, _used_llm = llm_or_fallback(
        system_prompt=system_prompt_for_language(state.get("report_language")),
        task_prompt=UNDERSTAND_PAPER_PROMPT,
        schema_model=PaperUnderstanding,
        fallback=fallback,
        context=context_block(context),
        extra=(
            f"Paper title: {metadata.title}\n"
            f"Abstract: {metadata.abstract}\n"
            f"Classification: {state['classification'].model_dump_json()}"
        ),
        model_name=state.get("model_name"),
    )
    return {"understanding": understanding, "status": "understood"}
