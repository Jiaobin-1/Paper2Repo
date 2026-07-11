from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture()
def client_with_token(isolated_settings, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("API_AUTH_TOKEN", "s3cret")
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


def test_health_and_docs_are_exempt(client_with_token: TestClient) -> None:
    assert client_with_token.get("/health").status_code == 200
    assert client_with_token.get("/docs").status_code == 200


def test_api_requires_bearer_token(client_with_token: TestClient) -> None:
    response = client_with_token.get("/api/runs")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_api_rejects_wrong_token(client_with_token: TestClient) -> None:
    response = client_with_token.get(
        "/api/runs",
        headers={"Authorization": "Bearer nope"},
    )

    assert response.status_code == 401


def test_api_accepts_correct_token(client_with_token: TestClient) -> None:
    response = client_with_token.get(
        "/api/runs",
        headers={"Authorization": "Bearer s3cret"},
    )

    assert response.status_code == 200


def test_api_is_open_by_default(isolated_settings) -> None:
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        assert client.get("/api/runs").status_code == 200
