from __future__ import annotations

from collections.abc import Mapping
from typing import Any

QUALITY_SECTIONS = (
    ("understanding", "理解", "Understanding"),
    ("method_analysis", "方法", "Method"),
    ("experiment_analysis", "实验", "Experiments"),
    ("reproduction_plan", "复现计划", "Reproduction Plan"),
)

TEMPLATE_FALLBACK_PHRASES = (
    "该模块来自方法相关片段的关键词抽取",
    "from method-related keyword extraction",
    "keyword extraction",
)


def evaluate_report_quality_signals(state: Mapping[str, Any], report_content: str = "") -> dict[str, Any]:
    section_evidence: dict[str, int] = {}
    missing_items = 0
    low_confidence_items = 0

    for key, _, _ in QUALITY_SECTIONS:
        payload = _model_dict(state.get(key))
        section_evidence[key] = len(payload.get("evidence_refs") or [])
        missing_items += len(payload.get("missing_items") or [])
        if key == "reproduction_plan":
            missing_items += len(payload.get("blocking_missing_items") or [])
        low_confidence_items += _count_low_confidence(payload)

    evidence_sections = sum(1 for count in section_evidence.values() if count > 0)
    evidence_coverage = evidence_sections / len(QUALITY_SECTIONS)
    fallback_phrase_count = _count_template_fallbacks(report_content)
    node_error_count = len(state.get("node_errors") or [])
    parsed = state.get("parsed_paper")
    extraction_bonus = 1.0 if parsed and getattr(parsed, "page_count", 0) > 0 else 0.0
    penalty = min(0.35, fallback_phrase_count * 0.04 + low_confidence_items * 0.015 + node_error_count * 0.08)
    score = max(0.0, min(1.0, evidence_coverage * 0.7 + extraction_bonus * 0.3 - penalty))

    return {
        "score": round(score, 4),
        "evidence_sections": evidence_sections,
        "total_sections": len(QUALITY_SECTIONS),
        "evidence_coverage": round(evidence_coverage, 4),
        "section_evidence": section_evidence,
        "missing_items": missing_items,
        "low_confidence_items": low_confidence_items,
        "fallback_phrase_count": fallback_phrase_count,
        "node_error_count": node_error_count,
        "recommendations": _recommendations(
            evidence_coverage=evidence_coverage,
            low_confidence_items=low_confidence_items,
            fallback_phrase_count=fallback_phrase_count,
            node_error_count=node_error_count,
        ),
    }


def build_report_quality_appendix(
    state: Mapping[str, Any],
    report_content: str,
    language: str,
) -> str:
    signals = evaluate_report_quality_signals(state, report_content)
    if language == "en":
        lines = [
            "\n\n---\n\n## Report Quality Signals\n\n",
            f"- Quality score: {signals['score']:.2f}\n",
            f"- Evidence-backed sections: {signals['evidence_sections']}/{signals['total_sections']}\n",
            f"- Low-confidence items: {signals['low_confidence_items']}\n",
            f"- Missing or blocking items: {signals['missing_items']}\n",
            f"- Template fallback signals: {signals['fallback_phrase_count']}\n",
            f"- Recoverable node errors: {signals['node_error_count']}\n",
            "\n### Evidence coverage by section\n\n",
        ]
        for key, _, en_label in QUALITY_SECTIONS:
            lines.append(f"- {en_label}: {signals['section_evidence'][key]} evidence references\n")
        lines.extend(
            [
                "\n### Recommended checks\n\n",
                _bullets(_recommendations_for_language(signals["recommendations"], "en"), "No immediate quality warnings."),
            ]
        )
        return "".join(lines)

    lines = [
        "\n\n---\n\n## 报告质量信号\n\n",
        f"- 质量评分：{signals['score']:.2f}\n",
        f"- 有证据支撑的章节：{signals['evidence_sections']}/{signals['total_sections']}\n",
        f"- 低置信度条目：{signals['low_confidence_items']}\n",
        f"- 缺失或阻塞项：{signals['missing_items']}\n",
        f"- 模板化 fallback 信号：{signals['fallback_phrase_count']}\n",
        f"- 可恢复节点错误：{signals['node_error_count']}\n",
        "\n### 各章节证据覆盖\n\n",
    ]
    for key, zh_label, _ in QUALITY_SECTIONS:
        lines.append(f"- {zh_label}：{signals['section_evidence'][key]} 条证据引用\n")
    lines.extend(["\n### 建议核查\n\n", _bullets(_recommendations_for_language(signals["recommendations"], "zh"), "暂无明显质量警告。")])
    return "".join(lines)


def _recommendations(
    *,
    evidence_coverage: float,
    low_confidence_items: int,
    fallback_phrase_count: int,
    node_error_count: int,
) -> list[str]:
    recommendations: list[str] = []
    if evidence_coverage < 1.0:
        recommendations.append("补查证据引用为 0 的章节，优先核对原文 method/experiment 段落。")
    if low_confidence_items:
        recommendations.append("优先人工复核低置信度模块、假设和限制项。")
    if fallback_phrase_count:
        recommendations.append("报告中存在模板化 fallback 表述，建议补充论文原文证据后再用于正式复现。")
    if node_error_count:
        recommendations.append("部分非关键节点失败，建议查看错误附录并重新运行。")
    return recommendations


def _recommendations_for_language(items: list[str], language: str) -> list[str]:
    if language != "en":
        return items
    translations = {
        "补查证据引用为 0 的章节，优先核对原文 method/experiment 段落。": (
            "Review sections with zero evidence references, starting with the method and experiment passages."
        ),
        "优先人工复核低置信度模块、假设和限制项。": (
            "Manually review low-confidence modules, assumptions, and limitations first."
        ),
        "报告中存在模板化 fallback 表述，建议补充论文原文证据后再用于正式复现。": (
            "The report contains fallback template wording; add source evidence before using it for formal reproduction."
        ),
        "部分非关键节点失败，建议查看错误附录并重新运行。": (
            "Some recoverable nodes failed; inspect the error appendix and rerun if needed."
        ),
    }
    return [translations.get(item, item) for item in items]


def _count_low_confidence(value: Any) -> int:
    if isinstance(value, dict):
        count = 1 if value.get("confidence") == "low" else 0
        return count + sum(_count_low_confidence(item) for item in value.values())
    if isinstance(value, list):
        return sum(_count_low_confidence(item) for item in value)
    return 0


def _count_template_fallbacks(report_content: str) -> int:
    lowered = report_content.lower()
    return sum(lowered.count(phrase.lower()) for phrase in TEMPLATE_FALLBACK_PHRASES)


def _bullets(items: list[str], empty: str) -> str:
    if not items:
        return f"- {empty}\n"
    return "".join(f"- {item}\n" for item in items)


def _model_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value if isinstance(value, dict) else {}
