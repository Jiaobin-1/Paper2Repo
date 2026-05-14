from typing import Literal

from pydantic import BaseModel, Field

PaperType = Literal[
    "supervised_learning",
    "benchmark_or_evaluation",
    "llm_application",
    "rag_or_retrieval",
    "agent_or_tool_use",
    "reinforcement_learning",
    "self_training_or_self_evolution",
    "dataset_or_benchmark_construction",
    "system_or_framework",
    "algorithm_or_theory",
    "multimodal",
    "cv_or_nlp_classic",
]


class PaperTypeClassification(BaseModel):
    paper_types: list[PaperType] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    required_resources: list[str] = Field(default_factory=list)
    likely_blockers: list[str] = Field(default_factory=list)
