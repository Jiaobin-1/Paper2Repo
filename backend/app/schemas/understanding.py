from pydantic import BaseModel, Field

from app.schemas.common import EvidenceRef, MissingItem


class ReadingTask(BaseModel):
    item: str
    status: str = "unclear"
    evidence: list[EvidenceRef] = Field(default_factory=list)
    next_action: str = ""


class PaperUnderstanding(BaseModel):
    background: str = ""
    core_problem: str = ""
    main_contributions: list[str] = Field(default_factory=list)
    overall_idea: str = ""
    conclusion: str = ""
    limitations: list[str] = Field(default_factory=list)
    applicable_scenarios: list[str] = Field(default_factory=list)
    key_assumptions: list[str] = Field(default_factory=list)
    reading_tasks: list[ReadingTask] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    missing_items: list[MissingItem] = Field(default_factory=list)
