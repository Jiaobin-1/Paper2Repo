from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture()
def client_with_token(isolated_settings, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("API_AUTH_TOKEN", "s3cret")
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        yield client
    get_settings.cache_clear()


def test_health_is_exempt(client_with_token: TestClient) -> None:
    assert client_with_token.get("/health").status_code == 200


def test_api_requires_token(client_with_token: TestClient) -> None:
    resp = client_with_token.get("/api/runs")
    assert resp.status_code == 401


def test_api_rejects_wrong_token(client_with_token: TestClient) -> None:
    resp = client_with_token.get("/api/runs", headers={"Authorization": "Bearer nope"})
    assert resp.status_code == 401


def test_api_accepts_correct_token(client_with_token: TestClient) -> None:
    resp = client_with_token.get("/api/runs", headers={"Authorization": "Bearer s3cret"})
    assert resp.status_code != 401


def test_open_by_default(isolated_settings) -> None:
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        assert client.get("/api/runs").status_code != 401
