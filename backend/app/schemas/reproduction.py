from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import EvidenceRef, MissingItem


class ReproductionModule(BaseModel):
    name: str
    purpose: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    todos: list[str] = Field(default_factory=list)


class CodeStructureItem(BaseModel):
    path: str
    type: Literal["file", "directory"] = "file"
    purpose: str = ""
    todo: str = ""


class ImplementationStep(BaseModel):
    step: int = Field(..., ge=1)
    title: str
    description: str
    expected_output: str = ""


class ChecklistItem(BaseModel):
    item: str
    done: bool = False


class RiskPoint(BaseModel):
    risk: str
    impact: Literal["low", "medium", "high"] = "medium"
    mitigation: str = ""


class ReproductionPlan(BaseModel):
    feasibility_summary: str = ""
    full_reproduction_difficulty: Literal["low", "medium", "high"] = "medium"
    mvp_pipeline_feasibility: Literal["low", "medium", "high"] = "medium"
    dependency_availability_difficulty: Literal["low", "medium", "high"] = "medium"
    data_availability_difficulty: Literal["low", "medium", "high"] = "medium"
    compute_cost_difficulty: Literal["low", "medium", "high"] = "medium"
    implementation_complexity_difficulty: Literal["low", "medium", "high"] = "medium"
    report_confidence: Literal["low", "medium", "high"] = "medium"
    audit_summary: str = ""
    recommended_first_experiment: str = ""
    minimum_reproduction_goal: Literal[
        "paper_faithful_reproduction",
        "pipeline_reproduction",
        "sanity_check_reproduction",
    ] = "pipeline_reproduction"
    reproduction_scope: list[str] = Field(default_factory=list)
    required_modules: list[ReproductionModule] = Field(default_factory=list)
    dataset_plan: list[str] = Field(default_factory=list)
    evaluation_plan: list[str] = Field(default_factory=list)
    code_structure: list[CodeStructureItem] = Field(default_factory=list)
    implementation_steps: list[ImplementationStep] = Field(default_factory=list)
    experiment_checklist: list[ChecklistItem] = Field(default_factory=list)
    risk_points: list[RiskPoint] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    blocking_missing_items: list[MissingItem] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    suggested_simplifications: list[str] = Field(default_factory=list)
