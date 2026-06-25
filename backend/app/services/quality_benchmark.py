from __future__ import annotations

from typing import Any


def evaluate_analysis_quality(
    state: dict[str, Any],
    expectations: dict[str, Any],
) -> dict[str, Any]:
    metadata = _model_dict(state.get("metadata"))
    experiments = _model_dict(state.get("experiment_analysis"))
    report_model = state.get("markdown_report")
    report = str(getattr(report_model, "content", "") or "")
    title = str(metadata.get("title") or "")
    searchable = f"{report}\n{experiments}".lower()

    title_score = _term_coverage(title, expectations.get("expected_title_terms", []))
    report_terms_score = _term_coverage(report, expectations.get("required_report_terms", []))
    dataset_score = _term_coverage(searchable, expectations.get("expected_dataset_terms", []))
    evidence_count = _count_evidence(state)
    minimum_evidence = max(1, int(expectations.get("minimum_evidence_refs", 1)))
    evidence_score = min(1.0, evidence_count / minimum_evidence)
    chunk_count = int(getattr(state.get("chunked_paper"), "chunk_count", 0) or 0)
    minimum_chunks = max(1, int(expectations.get("minimum_chunks", 1)))
    chunk_score = min(1.0, chunk_count / minimum_chunks)
    minimum_report_chars = max(1, int(expectations.get("minimum_report_chars", 1)))
    report_length_score = min(1.0, len(report) / minimum_report_chars)
    parsed = state.get("parsed_paper")
    extraction_score = 1.0 if parsed and getattr(parsed, "page_count", 0) > 0 else 0.0

    components = {
        "title_terms": round(title_score, 4),
        "report_terms": round(report_terms_score, 4),
        "dataset_terms": round(dataset_score, 4),
        "evidence": round(evidence_score, 4),
        "chunks": round(chunk_score, 4),
        "report_length": round(report_length_score, 4),
        "extraction": round(extraction_score, 4),
    }
    score = (
        title_score * 0.20
        + report_terms_score * 0.15
        + dataset_score * 0.15
        + evidence_score * 0.20
        + chunk_score * 0.10
        + report_length_score * 0.10
        + extraction_score * 0.10
    )
    threshold = float(expectations.get("minimum_score", 0.75))
    return {
        "score": round(score, 4),
        "minimum_score": threshold,
        "passed": score >= threshold,
        "components": components,
        "observations": {
            "title": title,
            "chunk_count": chunk_count,
            "evidence_count": evidence_count,
            "report_chars": len(report),
            "ocr_page_count": int(getattr(parsed, "ocr_page_count", 0) or 0) if parsed else 0,
            "table_count": int(getattr(parsed, "table_count", 0) or 0) if parsed else 0,
            "formula_count": int(getattr(parsed, "formula_count", 0) or 0) if parsed else 0,
        },
    }


def _term_coverage(text: str, terms: list[str]) -> float:
    if not terms:
        return 1.0
    haystack = text.lower()
    matches = sum(1 for term in terms if str(term).lower() in haystack)
    return matches / len(terms)


def _count_evidence(state: dict[str, Any]) -> int:
    total = 0
    for key in ("understanding", "method_analysis", "experiment_analysis", "reproduction_plan"):
        payload = _model_dict(state.get(key))
        total += len(payload.get("evidence_refs") or [])
    return total


def _model_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value if isinstance(value, dict) else {}
