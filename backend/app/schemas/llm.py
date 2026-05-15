from pydantic import BaseModel


class LLMConfigResponse(BaseModel):
    configured: bool
    base_url: str
    default_model: str
    available_models: list[str]
    timeout_seconds: float


class LLMConfigUpdateRequest(BaseModel):
    default_model: str


class LLMCheckResponse(BaseModel):
    configured: bool
    ok: bool
    base_url: str
    model: str
    timeout_seconds: float
    latency_ms: float | None = None
    error: str | None = None
