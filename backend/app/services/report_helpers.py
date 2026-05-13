from __future__ import annotations

from app.schemas.common import EvidenceRef, MissingItem
from app.schemas.experiments import ExperimentAnalysis
from app.schemas.understanding import PaperUnderstanding
from app.services.report_lang import Lang


def _cell(value: str) -> str:
    return " ".join(str(value or "").replace("|", "\\|").split())


def _label(map: dict[str, str], value: str) -> str:
    return map.get(value, value)


def _bullets(items: list[str], lang: Lang) -> str:
    if not items:
        return lang.no_items
    return "\n".join(f"- {item}" for item in items) + "\n"


def _checkboxes(items: list[str], lang: Lang) -> str:
    if not items:
        return lang.no_checklist
    return "\n".join(f"- [ ] {item}" for item in items) + "\n"


def _value(value: str, lang: Lang) -> str:
    return value if value else lang.no_value


def _evidence_table(items: list[EvidenceRef], lang: Lang) -> str:
    if not items:
        return (
            f"| {lang.ev_claim} | {lang.ev_location} | {lang.ev_section} | {lang.ev_quote} |\n"
            f"| --- | --- | --- | --- |\n"
            f"{lang.ev_empty_row}"
        )
    rows = [
        f"| {lang.ev_claim} | {lang.ev_location} | {lang.ev_section} | {lang.ev_quote} |",
        "| --- | --- | --- | --- |",
    ]
    seen: set[tuple[str, str, str]] = set()
    for item in items:
        key = (item.claim, item.page, item.quote)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            "| "
            + " | ".join([
                _cell(item.claim or lang.ev_no_claim),
                _cell(item.page or lang.ev_no_location),
                _cell(item.section or item.role or lang.ev_no_section),
                _cell(item.quote or lang.ev_no_quote),
            ])
            + " |"
        )
    return "\n".join(rows) + "\n"


def _missing_table(items: list[MissingItem], lang: Lang) -> str:
    if not items:
        return (
            f"| {lang.ms_category} | {lang.ms_severity} | {lang.ms_gap} | {lang.ms_action} |\n"
            f"| --- | --- | --- | --- |\n"
            f"| {' | '.join(_cell(v) for v in lang.ms_empty_row)} |\n"
        )
    rows = [
        f"| {lang.ms_category} | {lang.ms_severity} | {lang.ms_gap} | {lang.ms_action} |",
        "| --- | --- | --- | --- |",
    ]
    for item in items:
        rows.append(
            "| "
            + " | ".join([
                _cell(item.category),
                _cell(_label(lang.level_labels, item.severity)),
                _cell(item.item),
                _cell(item.suggested_action or item.evidence_or_reason or ("To be filled" if lang.lang_code == "en" else "待补充")),
            ])
            + " |"
        )
    return "\n".join(rows) + "\n"


def _experiment_matrix(experiments: ExperimentAnalysis, lang: Lang) -> str:
    if not experiments.reproduction_matrix:
        return (
            f"| {lang.mx_target} | {lang.mx_dataset} | {lang.mx_baseline} | {lang.mx_metric} "
            f"| {lang.mx_protocol} | {lang.mx_result} | {lang.mx_status} | {lang.mx_gaps} |\n"
            f"| --- | --- | --- | --- | --- | --- | --- | --- |\n"
            f"| {' | '.join(_cell(v) for v in lang.mx_empty_row)} |\n"
        )
    rows = [
        f"| {lang.mx_target} | {lang.mx_dataset} | {lang.mx_baseline} | {lang.mx_metric} "
        f"| {lang.mx_protocol} | {lang.mx_result} | {lang.mx_status} | {lang.mx_gaps} |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in experiments.reproduction_matrix:
        rows.append(
            "| "
            + " | ".join([
                _cell(item.target or lang.m_not_specified),
                _cell(item.dataset or lang.m_not_specified),
                _cell(item.baseline or lang.m_not_specified),
                _cell(item.metric or lang.m_not_specified),
                _cell(item.protocol or lang.m_not_specified),
                _cell(item.reported_result or lang.m_not_specified),
                _cell(_label(lang.status_labels, item.reproducibility_status or "unclear")),
                _cell("; ".join(item.missing_items) if item.missing_items else ("None" if lang.lang_code == "en" else "暂无")),
            ])
            + " |"
        )
    return "\n".join(rows) + "\n"


def _reading_tasks(understanding: PaperUnderstanding, lang: Lang) -> str:
    if not understanding.reading_tasks:
        return lang.rt_empty
    lines = []
    for task in understanding.reading_tasks:
        evidence = "; ".join(f"{item.page} {item.section}: {item.quote}" for item in task.evidence[:2]) or lang.rt_no_evidence
        lines.append(
            f"- [ ] **{_label(lang.status_labels, task.status)}**：{task.item} "
            f"{'证据' if lang.lang_code == 'zh' else 'Evidence'}: {evidence} "
            f"{'下一步' if lang.lang_code == 'zh' else 'Next'}: {task.next_action or lang.rt_next_fallback}"
        )
    return "\n".join(lines) + "\n"
