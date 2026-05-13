from pydantic import BaseModel, Field

from app.schemas.common import EvidenceRef, MissingItem


class DatasetInfo(BaseModel):
    name: str
    role: str = ""
    notes: str = ""
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ExperimentMatrixItem(BaseModel):
    target: str = ""
    dataset: str = ""
    baseline: str = ""
    metric: str = ""
    protocol: str = ""
    reported_result: str = ""
    reproducibility_status: str = "unclear"
    missing_items: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ExperimentAnalysis(BaseModel):
    datasets: list[DatasetInfo] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)
    main_results: list[str] = Field(default_factory=list)
    ablation_studies: list[str] = Field(default_factory=list)
    training_details: list[str] = Field(default_factory=list)
    evaluation_protocol: str = ""
    reproduction_matrix: list[ExperimentMatrixItem] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    missing_items: list[MissingItem] = Field(default_factory=list)
