from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    name: str
    role: str = ""
    notes: str = ""


class ExperimentAnalysis(BaseModel):
    datasets: list[DatasetInfo] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    baselines: list[str] = Field(default_factory=list)
    main_results: list[str] = Field(default_factory=list)
    ablation_studies: list[str] = Field(default_factory=list)
    training_details: list[str] = Field(default_factory=list)
    evaluation_protocol: str = ""
