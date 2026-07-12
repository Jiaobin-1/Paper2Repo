from pydantic import BaseModel, Field


class CompareMetadataSummary(BaseModel):
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    venue: str = ""
    year: str = ""
    keywords: list[str] = Field(default_factory=list)


class CompareUnderstandingSummary(BaseModel):
    background: str = ""
    core_problem: str = ""
    main_contributions: list[str] = Field(default_factory=list)
    overall_idea: str = ""


class CompareMethodSummary(BaseModel):
    method_summary: str = ""
    module_names: list[str] = Field(default_factory=list)
    system_framework: str = ""
    key_formulas: list[str] = Field(default_factory=list)

    # Exact legacy aliases retained for existing API consumers.
    pipeline_overview: str = ""
    architecture: str = ""


class CompareExperimentsSummary(BaseModel):
    datasets: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)
    main_results: list[str] = Field(default_factory=list)


class CompareRiskPoint(BaseModel):
    risk: str
    impact: str = ""
    mitigation: str = ""


class CompareChecklistItem(BaseModel):
    item: str
    done: bool = False


class CompareReproductionSummary(BaseModel):
    minimum_reproduction_goal: str = ""
    full_reproduction_difficulty: str = ""
    mvp_pipeline_feasibility: str = ""
    risk_points: list[CompareRiskPoint] = Field(default_factory=list)
    experiment_checklist: list[CompareChecklistItem] = Field(default_factory=list)

    # Exact legacy aliases retained for existing API consumers.
    reproduction_goal: str = ""
    risks: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)


class CompareRunResponse(BaseModel):
    run_id: str
    paper_id: str
    paper_title: str | None = None
    paper_filename: str | None = None
    model_name: str | None = None
    created_at: str
    report_title: str | None = None
    report_content: str | None = None
    metadata: CompareMetadataSummary
    understanding: CompareUnderstandingSummary
    method: CompareMethodSummary
    experiments: CompareExperimentsSummary
    reproduction: CompareReproductionSummary


class AvailableCompareRunResponse(BaseModel):
    run_id: str
    paper_id: str
    paper_title: str | None = None
    paper_filename: str | None = None
    model_name: str | None = None
    created_at: str
