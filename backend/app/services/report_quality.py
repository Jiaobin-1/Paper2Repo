from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ReportQualityCheck:
    name: str
    passed: bool
    score: float
    max_score: float
    message: str


@dataclass(frozen=True)
class ReportQualityResult:
    score: float
    max_score: float
    passed: bool
    checks: list[ReportQualityCheck]

    @property
    def ratio(self) -> float:
        if self.max_score <= 0:
            return 1.0
        return self.score / self.max_score

    @property
    def failures(self) -> list[ReportQualityCheck]:
        return [check for check in self.checks if not check.passed]


def evaluate_markdown_report(markdown: str, expectations: dict[str, Any]) -> ReportQualityResult:
    checks = [
        _required_sections_check(markdown, expectations.get("required_sections", [])),
        _required_terms_check(markdown, expectations.get("required_terms", {})),
        _evidence_check(markdown, int(expectations.get("min_evidence_refs", 0))),
        _missing_items_check(markdown, int(expectations.get("min_missing_items", 0))),
        _action_items_check(markdown, int(expectations.get("min_action_items", 0))),
        _forbidden_phrases_check(markdown, expectations.get("forbidden_phrases", [])),
    ]
    score = sum(check.score for check in checks)
    max_score = sum(check.max_score for check in checks)
    threshold = float(expectations.get("min_score_ratio", 0.8))
    return ReportQualityResult(
        score=score,
        max_score=max_score,
        passed=bool(checks) and all(check.passed for check in checks) and (score / max_score if max_score else 1.0) >= threshold,
        checks=checks,
    )


def assert_report_quality(markdown: str, expectations: dict[str, Any]) -> ReportQualityResult:
    result = evaluate_markdown_report(markdown, expectations)
    if result.passed:
        return result
    details = "; ".join(f"{check.name}: {check.message}" for check in result.failures)
    raise AssertionError(f"Report quality gate failed ({result.score:.1f}/{result.max_score:.1f}): {details}")


def _required_sections_check(markdown: str, sections: list[str]) -> ReportQualityCheck:
    missing = [section for section in sections if section.lower() not in markdown.lower()]
    passed = not missing
    max_score = 3.0
    score = max_score if passed else max_score * (len(sections) - len(missing)) / max(1, len(sections))
    return ReportQualityCheck(
        name="required_sections",
        passed=passed,
        score=score,
        max_score=max_score,
        message="all required sections found" if passed else f"missing sections: {', '.join(missing)}",
    )


def _required_terms_check(markdown: str, groups: dict[str, list[str]]) -> ReportQualityCheck:
    missing_groups: list[str] = []
    matched = 0
    for group, terms in groups.items():
        if any(term.lower() in markdown.lower() for term in terms):
            matched += 1
        else:
            missing_groups.append(group)
    passed = not missing_groups
    max_score = 3.0
    score = max_score if passed else max_score * matched / max(1, len(groups))
    return ReportQualityCheck(
        name="required_terms",
        passed=passed,
        score=score,
        max_score=max_score,
        message="all required term groups found" if passed else f"missing term groups: {', '.join(missing_groups)}",
    )


def _evidence_check(markdown: str, minimum: int) -> ReportQualityCheck:
    if minimum <= 0:
        return ReportQualityCheck("evidence_refs", True, 1.0, 1.0, "no minimum evidence count configured")
    evidence_count = len(re.findall(r"\bp\.\s*\d+\b|Evidence|证据", markdown, flags=re.IGNORECASE))
    passed = evidence_count >= minimum
    max_score = 2.0
    score = max_score if passed else max_score * evidence_count / minimum
    return ReportQualityCheck(
        name="evidence_refs",
        passed=passed,
        score=score,
        max_score=max_score,
        message=f"found {evidence_count} evidence references, expected at least {minimum}",
    )


def _missing_items_check(markdown: str, minimum: int) -> ReportQualityCheck:
    if minimum <= 0:
        return ReportQualityCheck("missing_items", True, 1.0, 1.0, "no minimum missing item count configured")
    missing_count = len(re.findall(r"missing|缺少|未说明|not specified|blocker|阻塞", markdown, flags=re.IGNORECASE))
    passed = missing_count >= minimum
    max_score = 1.5
    score = max_score if passed else max_score * missing_count / minimum
    return ReportQualityCheck(
        name="missing_items",
        passed=passed,
        score=score,
        max_score=max_score,
        message=f"found {missing_count} missing-item signals, expected at least {minimum}",
    )


def _action_items_check(markdown: str, minimum: int) -> ReportQualityCheck:
    if minimum <= 0:
        return ReportQualityCheck("action_items", True, 1.0, 1.0, "no minimum action item count configured")
    action_count = len(re.findall(r"- \[[ x]\]|\bStep\s+\d+|\d+\.\s+\*\*|验收|TODO", markdown, flags=re.IGNORECASE))
    passed = action_count >= minimum
    max_score = 1.5
    score = max_score if passed else max_score * action_count / minimum
    return ReportQualityCheck(
        name="action_items",
        passed=passed,
        score=score,
        max_score=max_score,
        message=f"found {action_count} action items, expected at least {minimum}",
    )


def _forbidden_phrases_check(markdown: str, phrases: list[str]) -> ReportQualityCheck:
    found = [phrase for phrase in phrases if phrase.lower() in markdown.lower()]
    passed = not found
    return ReportQualityCheck(
        name="forbidden_phrases",
        passed=passed,
        score=1.0 if passed else 0.0,
        max_score=1.0,
        message="no forbidden phrases found" if passed else f"found forbidden phrases: {', '.join(found)}",
    )
