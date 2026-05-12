from app.agents.state import PaperAnalysisState
from app.agents.prompts import COMMON_SYSTEM_PROMPT, UNDERSTAND_PAPER_PROMPT
from app.agents.nodes.node_utils import context_block, evidence_sentence, extract_sentences, llm_or_fallback
from app.schemas.understanding import PaperUnderstanding
from app.services.retrieval import retrieve_context


def understand_paper_node(state: PaperAnalysisState) -> PaperAnalysisState:
    chunks = state["chunked_paper"].chunks
    context = retrieve_context(
        chunks,
        query="paper background problem contribution conclusion",
        section_hints=["abstract", "introduction", "conclusion"],
        keywords=["problem", "contribution", "propose", "result", "conclusion"],
        top_k=8,
    )
    metadata = state["metadata"]

    contribution_sentences = extract_sentences(
        context,
        ["contribution", "we propose", "we present", "we introduce", "our method", "novel"],
        limit=4,
    )
    limitation_sentences = extract_sentences(context, ["limitation", "future work", "fail", "cannot", "however"], limit=3)
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
    )
    understanding, _used_llm = llm_or_fallback(
        system_prompt=COMMON_SYSTEM_PROMPT,
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
