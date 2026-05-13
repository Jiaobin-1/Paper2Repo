from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_settings_can_update_model_and_languages(isolated_settings):
    with TestClient(create_app()) as client:
        response = client.get("/api/settings")
        assert response.status_code == 200
        initial = response.json()
        assert initial["ui_language"] == "zh"
        assert initial["report_language"] == "en"

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
