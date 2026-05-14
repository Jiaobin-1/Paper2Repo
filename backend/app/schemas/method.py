from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import EvidenceRef, MissingItem


class MethodModule(BaseModel):
    module_name: str
    paper_section: str
    responsibility: str
    known_inputs: list[str] = Field(default_factory=list)
    inferred_inputs: list[str] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)
    known_outputs: list[str] = Field(default_factory=list)
    inferred_outputs: list[str] = Field(default_factory=list)
    missing_outputs: list[str] = Field(default_factory=list)
    key_parameters: list[str] = Field(default_factory=list)
    implementation_notes: list[str] = Field(default_factory=list)
    evidence_quote: str = ""
    confidence: Literal["low", "medium", "high"] = "medium"


class AlgorithmStep(BaseModel):
    step: int = Field(..., ge=1)
    name: str
    description: str
    evidence: list[EvidenceRef] = Field(default_factory=list)


class MethodAnalysis(BaseModel):
    method_summary: str = ""
    modules: list[MethodModule] = Field(default_factory=list)
    key_formulas: list[str] = Field(default_factory=list)
    algorithm_steps: list[AlgorithmStep] = Field(default_factory=list)
    system_framework: str = ""
    implementation_dependencies: list[str] = Field(default_factory=list)
    implementation_interfaces: list[str] = Field(default_factory=list)
    formula_or_pseudocode_gaps: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    missing_items: list[MissingItem] = Field(default_factory=list)
