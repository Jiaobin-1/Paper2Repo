from pydantic import BaseModel, Field


class MethodModule(BaseModel):
    name: str
    responsibility: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    implementation_notes: list[str] = Field(default_factory=list)


class AlgorithmStep(BaseModel):
    step: int = Field(..., ge=1)
    name: str
    description: str


class MethodAnalysis(BaseModel):
    method_summary: str = ""
    modules: list[MethodModule] = Field(default_factory=list)
    key_formulas: list[str] = Field(default_factory=list)
    algorithm_steps: list[AlgorithmStep] = Field(default_factory=list)
    system_framework: str = ""
    implementation_dependencies: list[str] = Field(default_factory=list)
