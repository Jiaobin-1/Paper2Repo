from typing import Literal

from pydantic import BaseModel, Field


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
    feasibility_level: Literal["high", "medium", "low"] = "medium"
    minimum_reproduction_goal: str = ""
    reproduction_scope: list[str] = Field(default_factory=list)
    required_modules: list[ReproductionModule] = Field(default_factory=list)
    dataset_plan: list[str] = Field(default_factory=list)
    evaluation_plan: list[str] = Field(default_factory=list)
    code_structure: list[CodeStructureItem] = Field(default_factory=list)
    implementation_steps: list[ImplementationStep] = Field(default_factory=list)
    experiment_checklist: list[ChecklistItem] = Field(default_factory=list)
    risk_points: list[RiskPoint] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    suggested_simplifications: list[str] = Field(default_factory=list)
