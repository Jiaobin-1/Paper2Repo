from pydantic import BaseModel, Field


class PaperUnderstanding(BaseModel):
    background: str = ""
    core_problem: str = ""
    main_contributions: list[str] = Field(default_factory=list)
    overall_idea: str = ""
    conclusion: str = ""
    limitations: list[str] = Field(default_factory=list)
    applicable_scenarios: list[str] = Field(default_factory=list)
