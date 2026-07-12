from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.core.database import get_analysis_result, get_paper, get_report, get_run, list_runs
from app.schemas.compare import (
    AvailableCompareRunResponse,
    CompareChecklistItem,
    CompareExperimentsSummary,
    CompareMetadataSummary,
    CompareMethodSummary,
    CompareReproductionSummary,
    CompareRiskPoint,
    CompareRunResponse,
    CompareUnderstandingSummary,
)

router = APIRouter(
    prefix="/compare",
    tags=["compare"],
)


@router.get(
    "",
    response_model=list[CompareRunResponse],
    summary="Compare analysis runs",
    description="Retrieve structured comparison data for multiple completed runs.",
)
def compare_runs(
    run_ids: str = Query(..., description="Comma-separated run IDs to compare"),
) -> list[CompareRunResponse]:
    ids = [rid.strip() for rid in run_ids.split(",") if rid.strip()]
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 run IDs are required.")
    if len(ids) > 4:
        raise HTTPException(status_code=400, detail="At most 4 runs can be compared.")

    results: list[CompareRunResponse] = []
    for run_id in ids:
        run = get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found.")
        if run["status"] != "completed":
            raise HTTPException(status_code=400, detail=f"Run {run_id} is not completed.")

        paper = get_paper(run["paper_id"])
        analysis = get_analysis_result(run_id)
        report = get_report(run_id)
        if not analysis:
            raise HTTPException(status_code=409, detail=f"Run {run_id} has no analysis result.")
        if not report or not _text(report.get("content")):
            raise HTTPException(status_code=409, detail=f"Run {run_id} has no completed report.")

        metadata = analysis.get("metadata_json") or {}
        understanding = analysis.get("understanding_json") or {}
        method = analysis.get("method_json") or {}
        experiments = analysis.get("experiments_json") or {}
        reproduction = analysis.get("reproduction_json") or {}

        results.append(
            CompareRunResponse(
                run_id=run_id,
                paper_id=run["paper_id"],
                paper_title=paper.get("title") if paper else None,
                paper_filename=paper.get("filename") if paper else None,
                model_name=run.get("model_name"),
                created_at=run["created_at"],
                report_title=report.get("title"),
                report_content=report.get("content"),
                metadata=_extract_metadata_summary(metadata),
                understanding=_extract_understanding_summary(understanding),
                method=_extract_method_summary(method),
                experiments=_extract_experiments_summary(experiments),
                reproduction=_extract_reproduction_summary(reproduction),
            )
        )

    return results


@router.get(
    "/available",
    response_model=list[AvailableCompareRunResponse],
    summary="List runs available for comparison",
    description="Retrieve completed runs that can be selected for comparison.",
)
def list_available_runs() -> list[AvailableCompareRunResponse]:
    runs = list_runs(limit=50)
    available: list[AvailableCompareRunResponse] = []
    for run in runs:
        if run["status"] == "completed" and _has_comparison_artifacts(run["id"]):
            paper = get_paper(run["paper_id"])
            available.append(
                AvailableCompareRunResponse(
                    run_id=run["id"],
                    paper_id=run["paper_id"],
                    paper_title=paper.get("title") if paper else None,
                    paper_filename=paper.get("filename") if paper else None,
                    model_name=run.get("model_name"),
                    created_at=run["created_at"],
                )
            )
    return available


def _has_comparison_artifacts(run_id: str) -> bool:
    analysis = get_analysis_result(run_id)
    report = get_report(run_id)
    return bool(analysis and report and _text(report.get("content")))


def _extract_metadata_summary(metadata: dict[str, Any] | None) -> CompareMetadataSummary:
    if not metadata:
        return CompareMetadataSummary()
    return CompareMetadataSummary(
        title=_text(metadata.get("title")),
        authors=_string_list(metadata.get("authors")),
        venue=_text(metadata.get("venue")),
        year=_text(metadata.get("year")),
        keywords=_string_list(metadata.get("keywords")),
    )


def _extract_understanding_summary(understanding: dict[str, Any] | None) -> CompareUnderstandingSummary:
    if not understanding:
        return CompareUnderstandingSummary()
    return CompareUnderstandingSummary(
        background=_text(understanding.get("background"), limit=300),
        core_problem=_text(understanding.get("core_problem"), limit=300),
        main_contributions=_string_list(understanding.get("main_contributions"), limit=5),
        overall_idea=_text(understanding.get("overall_idea"), limit=300),
    )


def _extract_method_summary(method: dict[str, Any] | None) -> CompareMethodSummary:
    if not method:
        return CompareMethodSummary()
    method_summary = _text(method.get("method_summary"), limit=300)
    system_framework = _text(method.get("system_framework"), limit=300)
    module_names: list[str] = []
    modules = method.get("modules")
    if isinstance(modules, list):
        for module in modules:
            if not isinstance(module, dict):
                continue
            module_name = _text(module.get("module_name") or module.get("name"))
            if module_name and module_name not in module_names:
                module_names.append(module_name)
            if len(module_names) >= 5:
                break
    return CompareMethodSummary(
        method_summary=method_summary,
        module_names=module_names,
        system_framework=system_framework,
        key_formulas=_string_list(method.get("key_formulas"), limit=5),
        pipeline_overview=method_summary,
        architecture=system_framework,
    )


def _extract_experiments_summary(experiments: dict[str, Any] | None) -> CompareExperimentsSummary:
    if not experiments:
        return CompareExperimentsSummary()
    datasets: list[str] = []
    raw_datasets = experiments.get("datasets")
    if isinstance(raw_datasets, list):
        for dataset in raw_datasets:
            name = _text(dataset.get("name")) if isinstance(dataset, dict) else _text(dataset)
            if name:
                datasets.append(name)
    return CompareExperimentsSummary(
        datasets=datasets,
        metrics=_string_list(experiments.get("metrics"), limit=5),
        baselines=_string_list(experiments.get("baselines"), limit=5),
        main_results=_string_list(experiments.get("main_results"), limit=5),
    )


def _extract_reproduction_summary(reproduction: dict[str, Any] | None) -> CompareReproductionSummary:
    if not reproduction:
        return CompareReproductionSummary()
    minimum_goal = _text(reproduction.get("minimum_reproduction_goal"), limit=300)
    risk_points = _extract_risk_points(reproduction.get("risk_points"))
    checklist = _extract_checklist(reproduction.get("experiment_checklist"))
    return CompareReproductionSummary(
        minimum_reproduction_goal=minimum_goal,
        full_reproduction_difficulty=_text(reproduction.get("full_reproduction_difficulty")),
        mvp_pipeline_feasibility=_text(reproduction.get("mvp_pipeline_feasibility")),
        risk_points=risk_points,
        experiment_checklist=checklist,
        reproduction_goal=minimum_goal,
        risks=[item.risk for item in risk_points],
        checklist=[item.item for item in checklist],
    )


def _extract_risk_points(value: Any) -> list[CompareRiskPoint]:
    if not isinstance(value, list):
        return []
    output: list[CompareRiskPoint] = []
    for raw in value[:3]:
        if isinstance(raw, dict):
            risk = _text(raw.get("risk"))
            impact = _text(raw.get("impact"))
            mitigation = _text(raw.get("mitigation"))
        else:
            risk = _text(raw)
            impact = ""
            mitigation = ""
        if risk:
            output.append(CompareRiskPoint(risk=risk, impact=impact, mitigation=mitigation))
    return output


def _extract_checklist(value: Any) -> list[CompareChecklistItem]:
    if not isinstance(value, list):
        return []
    output: list[CompareChecklistItem] = []
    for raw in value[:5]:
        if isinstance(raw, dict):
            item = _text(raw.get("item"))
            done = bool(raw.get("done", False))
        else:
            item = _text(raw)
            done = False
        if item:
            output.append(CompareChecklistItem(item=item, done=done))
    return output


def _string_list(value: Any, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [_text(item) for item in value]
    output = [item for item in items if item]
    return output[:limit] if limit is not None else output


def _text(value: Any, *, limit: int | None = None) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[:limit] if limit is not None else text
