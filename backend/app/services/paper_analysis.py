from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TypedDict

from app.schemas.chunks import PaperChunk, RetrievedChunk
from app.schemas.common import EvidenceRef, MissingItem
from app.services.retrieval import retrieve_context


class _AnalysisViewConfig(TypedDict):
    query: str
    section_hints: list[str]
    keywords: list[str]


SECTION_ROLES = {
    "abstract": ["abstract"],
    "intro": ["introduction", "background"],
    "related_work": ["related work"],
    "method": ["method", "methodology", "approach", "model", "algorithm", "framework"],
    "experiment": ["experiment", "evaluation", "result", "ablation", "analysis"],
    "conclusion": ["conclusion", "discussion", "limitation", "future work"],
    "appendix": ["appendix", "supplementary"],
    "reference": ["reference", "bibliography"],
}


ANALYSIS_VIEWS: dict[str, _AnalysisViewConfig] = {
    "understanding": {
        "query": "abstract introduction motivation problem contribution conclusion limitation",
        "section_hints": ["abstract", "introduction", "background", "conclusion", "limitations"],
        "keywords": ["problem", "challenge", "motivation", "contribution", "propose", "conclusion", "limitation"],
    },
    "method": {
        "query": "method approach model algorithm framework module objective loss pseudo code implementation",
        "section_hints": ["method", "methodology", "approach", "model", "algorithm"],
        "keywords": ["method", "approach", "framework", "module", "algorithm", "loss", "objective", "implementation"],
    },
    "experiment": {
        "query": "experiment dataset baseline metric evaluation result ablation training hyperparameter",
        "section_hints": ["experiment", "evaluation", "result", "ablation"],
        "keywords": ["dataset", "baseline", "metric", "evaluation", "ablation", "result", "training", "hyperparameter"],
    },
    "missing_info": {
        "query": "code data available hyperparameter implementation setting resource gpu license reproducibility",
        "section_hints": ["method", "experiment", "implementation", "appendix", "supplementary"],
        "keywords": ["code", "data", "available", "hyperparameter", "setting", "gpu", "resource", "license", "seed"],
    },
}


def section_role(section_title: str | None, content: str = "") -> str:
    title_haystack = (section_title or "").lower()
    for role, terms in SECTION_ROLES.items():
        if any(term in title_haystack for term in terms):
            return role

    haystack = content[:500].lower()
    for role, terms in SECTION_ROLES.items():
        if any(term in haystack for term in terms):
            return role
    if re.search(r"\b\d+\.?\s+(method|approach|model|algorithm)\b", haystack):
        return "method"
    if re.search(r"\b\d+\.?\s+(experiment|evaluation|results?)\b", haystack):
        return "experiment"
    return "other"


def chunk_role(chunk: PaperChunk | RetrievedChunk) -> str:
    return section_role(chunk.metadata.section_title, chunk.content)


def retrieve_analysis_context(
    chunks: list[PaperChunk],
    view: str,
    *,
    top_k: int = 10,
) -> list[RetrievedChunk]:
    config = ANALYSIS_VIEWS[view]
    return retrieve_context(
        chunks,
        query=config["query"],
        section_hints=config["section_hints"],
        keywords=config["keywords"],
        top_k=top_k,
    )


def evidence_from_chunk(
    item: RetrievedChunk,
    claim: str,
    *,
    keywords: Iterable[str] = (),
    max_quote_chars: int = 260,
) -> EvidenceRef:
    quote = _best_quote(item.content, keywords, max_chars=max_quote_chars)
    page = f"p.{item.metadata.page_start}"
    if item.metadata.page_start != item.metadata.page_end:
        page = f"pp.{item.metadata.page_start}-{item.metadata.page_end}"
    return EvidenceRef(
        claim=claim,
        page=page,
        section=item.metadata.section_title or "unknown",
        quote=quote,
        role=chunk_role(item),
    )


def collect_evidence(
    context: list[RetrievedChunk],
    claim: str,
    *,
    keywords: Iterable[str] = (),
    limit: int = 3,
) -> list[EvidenceRef]:
    evidence: list[EvidenceRef] = []
    seen: set[tuple[str, str]] = set()
    for item in context:
        ref = evidence_from_chunk(item, claim, keywords=keywords)
        key = (ref.page, ref.quote)
        if ref.quote and key not in seen:
            evidence.append(ref)
            seen.add(key)
        if len(evidence) >= limit:
            break
    return evidence


def audit_reproduction_gaps(
    *,
    datasets: list[str],
    metrics: list[str],
    baselines: list[str],
    training_details: list[str],
    method_dependencies: list[str],
    method_missing_items: list[MissingItem] | None = None,
    experiment_missing_items: list[MissingItem] | None = None,
    evidence_text: str = "",
) -> list[MissingItem]:
    gaps: list[MissingItem] = []
    if not datasets:
        gaps.append(
            _gap(
                "dataset",
                "未找到明确的数据集名称或数据来源。",
                "high",
                "实验复现无法确认输入数据。",
                "回到实验章节和附录核查 dataset、benchmark、data availability。",
            )
        )
    if not baselines:
        gaps.append(
            _gap(
                "baseline",
                "未找到可对照的 baseline 名称或配置。",
                "medium",
                "无法判断复现结果应与哪些方法比较。",
                "优先核查实验表格和 related work 中的比较方法。",
            )
        )
    if not metrics:
        gaps.append(
            _gap(
                "metric",
                "未找到明确的评价指标。",
                "high",
                "没有指标就无法验收最小复现实验。",
                "从实验表格表头、evaluation protocol 或 appendix 中补齐指标定义。",
            )
        )
    if not training_details:
        gaps.append(
            _gap(
                "hyperparameter",
                "未找到训练/推理设置、超参数或随机种子。",
                "medium",
                "结果差距难以归因，复现稳定性不足。",
                "核查 implementation details，并把未知超参数写入配置文件。",
            )
        )
    if not method_dependencies:
        gaps.append(
            _gap(
                "implementation_detail",
                "未找到足够明确的实现依赖或框架信息。",
                "medium",
                "工程选型和接口边界需要人工确认。",
                "先实现最小接口，再根据论文或开源代码补齐依赖。",
            )
        )

    lower = evidence_text.lower()
    if any(term in lower for term in ["gpu", "a100", "v100", "tpu", "cluster", "distributed"]):
        gaps.append(
            _gap(
                "compute",
                "论文片段出现较高算力或分布式训练信号。",
                "medium",
                "完整复现可能超出本地 MVP 资源。",
                "先选择 inference、small subset 或单卡可运行设置。",
            )
        )
    if any(term in lower for term in ["preprocess", "pre-processing", "tokenize", "filter"]):
        gaps.append(
            _gap(
                "preprocessing",
                "数据预处理规则需要单独核查。",
                "medium",
                "预处理差异会直接影响指标。",
                "把预处理写成独立脚本，并记录每一步输入输出。",
            )
        )
    if any(term in lower for term in ["weight", "checkpoint", "pretrained", "pre-trained"]) and "available" not in lower:
        gaps.append(
            _gap(
                "model_weight",
                "模型权重或 checkpoint 可用性不明确。",
                "medium",
                "无法确认是否能直接复现推理或微调结果。",
                "核查论文链接、附录和仓库说明中的 checkpoint 发布情况。",
            )
        )
    if "license" in lower:
        gaps.append(
            _gap(
                "license",
                "论文片段提到 license，需要确认数据或模型许可。",
                "low",
                "复现和发布结果可能受许可证约束。",
                "记录数据集、模型权重和代码的许可条款。",
            )
        )

    for item in [*(method_missing_items or []), *(experiment_missing_items or [])]:
        if not _has_gap(gaps, item.category, item.item):
            gaps.append(item)

    return gaps


def _best_quote(text: str, keywords: Iterable[str], max_chars: int) -> str:
    keyword_list = [keyword.lower() for keyword in keywords if keyword]
    sentences = _split_sentences(text)
    for sentence in sentences:
        normalized = _normalize_space(sentence)
        if not normalized:
            continue
        lower = normalized.lower()
        if keyword_list and any(keyword in lower for keyword in keyword_list):
            return normalized[:max_chars]
    for sentence in sentences:
        normalized = _normalize_space(sentence)
        if len(normalized) >= 20:
            return normalized[:max_chars]
    return _normalize_space(text)[:max_chars]


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _split_sentences(text: str) -> list[str]:
    normalized = _normalize_space(text)
    if not normalized:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?。！？])\s+", normalized) if part.strip()]


def _gap(category: str, item: str, severity: str, reason: str, action: str) -> MissingItem:
    return MissingItem(
        category=category,
        item=item,
        severity=severity,
        evidence_or_reason=reason,
        suggested_action=action,
    )


def _has_gap(gaps: list[MissingItem], category: str, item: str) -> bool:
    return any(gap.category == category and gap.item == item for gap in gaps)
