from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.database import get_default_model, set_default_model
from app.schemas.llm import LLMConfigResponse, LLMConfigUpdateRequest

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/config", response_model=LLMConfigResponse)
def get_llm_config() -> LLMConfigResponse:
    settings = get_settings()
    return LLMConfigResponse(
        configured=bool(settings.openai_api_key),
        base_url=settings.openai_base_url,
        default_model=get_default_model(),
        available_models=settings.available_openai_models,
    )


@router.put("/config", response_model=LLMConfigResponse)
def update_llm_config(payload: LLMConfigUpdateRequest) -> LLMConfigResponse:
    settings = get_settings()
    try:
        default_model = set_default_model(payload.default_model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return LLMConfigResponse(
        configured=bool(settings.openai_api_key),
        base_url=settings.openai_base_url,
        default_model=default_model,
        available_models=settings.available_openai_models,
    )
