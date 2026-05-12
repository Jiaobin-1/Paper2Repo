from pydantic import BaseModel


class LLMConfigResponse(BaseModel):
    configured: bool
    base_url: str
    default_model: str
    available_models: list[str]


class LLMConfigUpdateRequest(BaseModel):
    default_model: str
