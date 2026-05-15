from typing import Literal

from pydantic import BaseModel

LanguageCode = Literal["zh", "en"]
ThemeMode = Literal["light", "dark", "system"]


class AppSettingsResponse(BaseModel):
    configured: bool
    base_url: str
    default_model: str
    available_models: list[str]
    timeout_seconds: float
    ui_language: LanguageCode
    report_language: LanguageCode
    theme: ThemeMode


class AppSettingsUpdateRequest(BaseModel):
    default_model: str | None = None
    ui_language: LanguageCode | None = None
    report_language: LanguageCode | None = None
    theme: ThemeMode | None = None
