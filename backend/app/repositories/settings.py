from __future__ import annotations

import sqlite3

from app.core.config import get_settings
from app.repositories.connection import get_connection, utc_now

DEFAULT_MODEL_SETTING_KEY = "default_model"
UI_LANGUAGE_SETTING_KEY = "ui_language"
REPORT_LANGUAGE_SETTING_KEY = "report_language"
THEME_SETTING_KEY = "theme"
SUPPORTED_LANGUAGES = {"zh", "en"}
SUPPORTED_THEMES = {"light", "dark", "system"}

def _ensure_default_model_setting(conn: sqlite3.Connection) -> None:
    settings = get_settings()
    available_models = settings.available_openai_models
    configured_default = settings.openai_model.strip() or available_models[0]
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (DEFAULT_MODEL_SETTING_KEY,),
    ).fetchone()
    if row and row["value"] in available_models:
        return
    conn.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (DEFAULT_MODEL_SETTING_KEY, configured_default, utc_now()),
    )


def _ensure_language_settings(conn: sqlite3.Connection) -> None:
    _ensure_setting(conn, UI_LANGUAGE_SETTING_KEY, "zh", SUPPORTED_LANGUAGES)
    _ensure_setting(conn, REPORT_LANGUAGE_SETTING_KEY, "en", SUPPORTED_LANGUAGES)
    _ensure_setting(conn, THEME_SETTING_KEY, "light", SUPPORTED_THEMES)


def _ensure_setting(conn: sqlite3.Connection, key: str, default_value: str, allowed_values: set[str]) -> None:
    row = conn.execute(
        "SELECT value FROM app_settings WHERE key = ?",
        (key,),
    ).fetchone()
    if row and row["value"] in allowed_values:
        return
    conn.execute(
        """
        INSERT INTO app_settings (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = excluded.updated_at
        """,
        (key, default_value, utc_now()),
    )


def get_app_setting(key: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def set_app_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, utc_now()),
        )


def get_default_model() -> str:
    settings = get_settings()
    available_models = settings.available_openai_models
    stored_model = get_app_setting(DEFAULT_MODEL_SETTING_KEY)
    if stored_model in available_models:
        return stored_model
    default_model = settings.openai_model.strip() or available_models[0]
    set_app_setting(DEFAULT_MODEL_SETTING_KEY, default_model)
    return default_model


def set_default_model(model_name: str) -> str:
    normalized_model = model_name.strip()
    if normalized_model not in get_settings().available_openai_models:
        raise ValueError("Model is not listed in OPENAI_MODEL_OPTIONS.")
    set_app_setting(DEFAULT_MODEL_SETTING_KEY, normalized_model)
    return normalized_model


def get_ui_language() -> str:
    return _get_language_setting(UI_LANGUAGE_SETTING_KEY, "zh")


def set_ui_language(language: str) -> str:
    return _set_language_setting(UI_LANGUAGE_SETTING_KEY, language)


def get_report_language() -> str:
    return _get_language_setting(REPORT_LANGUAGE_SETTING_KEY, "en")


def set_report_language(language: str) -> str:
    return _set_language_setting(REPORT_LANGUAGE_SETTING_KEY, language)


def _get_language_setting(key: str, default_value: str) -> str:
    stored_language = get_app_setting(key)
    if stored_language in SUPPORTED_LANGUAGES:
        return stored_language
    set_app_setting(key, default_value)
    return default_value


def _set_language_setting(key: str, language: str) -> str:
    normalized_language = language.strip().lower()
    if normalized_language not in SUPPORTED_LANGUAGES:
        raise ValueError("Language must be zh or en.")
    set_app_setting(key, normalized_language)
    return normalized_language


def get_theme() -> str:
    stored_theme = get_app_setting(THEME_SETTING_KEY)
    if stored_theme in SUPPORTED_THEMES:
        return stored_theme
    set_app_setting(THEME_SETTING_KEY, "light")
    return "light"


def set_theme(theme: str) -> str:
    normalized_theme = theme.strip().lower()
    if normalized_theme not in SUPPORTED_THEMES:
        raise ValueError("Theme must be light, dark, or system.")
    set_app_setting(THEME_SETTING_KEY, normalized_theme)
    return normalized_theme
