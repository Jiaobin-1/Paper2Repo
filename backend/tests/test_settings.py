from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.services.llm_client import LLMClient


def test_settings_can_update_model_and_languages(isolated_settings):
    with TestClient(create_app()) as client:
        response = client.get("/api/settings")
        assert response.status_code == 200
        initial = response.json()
        assert initial["ui_language"] == "zh"
        assert initial["report_language"] == "en"
        assert initial["timeout_seconds"] == 60.0

        update_response = client.put(
            "/api/settings",
            json={
                "default_model": "test-model",
                "ui_language": "en",
                "report_language": "zh",
            },
        )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["default_model"] == "test-model"
    assert updated["ui_language"] == "en"
    assert updated["report_language"] == "zh"


def test_settings_reject_invalid_model(isolated_settings):
    with TestClient(create_app()) as client:
        response = client.put("/api/settings", json={"default_model": "missing-model"})

    assert response.status_code == 400


def test_llm_check_reports_unconfigured_without_network(isolated_settings):
    with TestClient(create_app()) as client:
        response = client.post("/api/llm/check")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["ok"] is False
    assert body["model"] == "test-model"


def test_llm_check_reports_success(isolated_settings, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
    monkeypatch.setattr(LLMClient, "chat", lambda self, **kwargs: "OK")

    with TestClient(create_app()) as client:
        response = client.post("/api/llm/check")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["ok"] is True
    assert body["model"] == "test-model"
    assert body["latency_ms"] is not None
