from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.database import get_default_model, set_default_model
from app.schemas.llm import LLMCheckResponse, LLMConfigResponse, LLMConfigUpdateRequest
from app.services.llm_client import LLMClient

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/config", response_model=LLMConfigResponse)
def get_llm_config() -> LLMConfigResponse:
    settings = get_settings()
    return LLMConfigResponse(
        configured=bool(settings.openai_api_key),
        base_url=settings.openai_base_url,
        default_model=get_default_model(),
        available_models=settings.available_openai_models,
        timeout_seconds=settings.openai_timeout_seconds,
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
        timeout_seconds=settings.openai_timeout_seconds,
    )


@router.post("/check", response_model=LLMCheckResponse)
def check_llm_connection() -> LLMCheckResponse:
    settings = get_settings()
    model = get_default_model()
    if not settings.openai_api_key:
        return LLMCheckResponse(
            configured=False,
            ok=False,
            base_url=settings.openai_base_url,
            model=model,
            timeout_seconds=settings.openai_timeout_seconds,
            error="OPENAI_API_KEY is not configured.",
        )

    client = LLMClient(model_name=model)
    start = time.perf_counter()
    try:
        client.chat(
            system_prompt="You are a connectivity probe. Reply with OK only.",
            messages=[{"role": "user", "content": "OK"}],
            temperature=0,
        )
    except Exception as exc:
        return LLMCheckResponse(
            configured=True,
            ok=False,
            base_url=settings.openai_base_url,
            model=model,
            timeout_seconds=settings.openai_timeout_seconds,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
            error=_public_error(exc, settings.openai_api_key),
        )

    return LLMCheckResponse(
        configured=True,
        ok=True,
        base_url=settings.openai_base_url,
        model=model,
        timeout_seconds=settings.openai_timeout_seconds,
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )


def _public_error(exc: Exception, secret: str) -> str:
    message = str(exc) or exc.__class__.__name__
    if secret:
        message = message.replace(secret, "***")
    return message[:500]
