from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException

from app.core.config import get_settings
from app.core.database import (
    get_default_model,
    get_report_language,
    get_ui_language,
    set_default_model,
    set_report_language,
    set_ui_language,
)
from app.schemas.settings import AppSettingsResponse, AppSettingsUpdateRequest, LanguageCode

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get(
    "",
    response_model=AppSettingsResponse,
    summary="Get app settings",
    description="Retrieve current application settings including model configuration and language preferences.",
)
def get_app_settings() -> AppSettingsResponse:
    return _settings_response()


@router.put(
    "",
    response_model=AppSettingsResponse,
    summary="Update app settings",
    description="Update application settings. Only provided fields will be updated.",
)
def update_app_settings(payload: AppSettingsUpdateRequest) -> AppSettingsResponse:
    try:
        if payload.default_model is not None:
            set_default_model(payload.default_model)
        if payload.ui_language is not None:
            set_ui_language(payload.ui_language)
        if payload.report_language is not None:
            set_report_language(payload.report_language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _settings_response()


def _settings_response() -> AppSettingsResponse:
    settings = get_settings()
    return AppSettingsResponse(
        configured=bool(settings.openai_api_key),
        base_url=settings.openai_base_url,
        default_model=get_default_model(),
        available_models=settings.available_openai_models,
        ui_language=cast(LanguageCode, get_ui_language()),
        report_language=cast(LanguageCode, get_report_language()),
    )
