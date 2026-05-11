from typing import Literal

from pydantic import BaseModel, Field


class PaperTypeClassification(BaseModel):
    domain: Literal[
        "llm",
        "agent",
        "rag",
        "nlp",
        "cv",
        "recommendation",
        "machine_learning",
        "deep_learning",
        "multimodal",
        "other",
    ] = "other"
    paper_type: Literal[
        "experimental",
        "system",
        "benchmark",
        "dataset",
        "theoretical",
        "survey",
        "other",
    ] = "experimental"
    reproduction_mode: Literal[
        "training_from_scratch",
        "fine_tuning",
        "inference_pipeline",
        "benchmark_evaluation",
        "ablation_reproduction",
        "not_recommended",
    ] = "benchmark_evaluation"
    difficulty: Literal["low", "medium", "high", "very_high"] = "medium"
    suitability_for_mvp: Literal["good", "partial", "poor"] = "partial"
    reasons: list[str] = Field(default_factory=list)
    required_resources: list[str] = Field(default_factory=list)
    likely_blockers: list[str] = Field(default_factory=list)
