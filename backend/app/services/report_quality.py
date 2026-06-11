from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


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
