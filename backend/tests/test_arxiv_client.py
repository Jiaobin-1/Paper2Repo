from __future__ import annotations

import io
from pathlib import Path

import pytest

from app.services import arxiv_client
from app.services.arxiv_client import _parse_arxiv_xml, download_arxiv_pdf, is_valid_arxiv_id

_ATOM = "http://www.w3.org/2005/Atom"


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


@pytest.mark.parametrize(
    "arxiv_id",
    ["2301.12345", "2301.12345v2", "1234.5678", "math.GT/0309136", "hep-th/9901001v3"],
)
def test_valid_ids_accepted(arxiv_id: str) -> None:
    assert is_valid_arxiv_id(arxiv_id)


@pytest.mark.parametrize(
    "arxiv_id",
    ["../../etc/passwd", "foo bar", "http://evil.com/x", "2301", "", "2301.12345v"],
)
def test_invalid_ids_rejected(arxiv_id: str) -> None:
    assert not is_valid_arxiv_id(arxiv_id)


def test_download_rejects_invalid_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unrecognized"):
        download_arxiv_pdf("../../evil", tmp_path)


def test_download_enforces_size_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b"%PDF-" + b"x" * (3 * 1024 * 1024)
    monkeypatch.setattr(arxiv_client, "urlopen", lambda *a, **k: _FakeResponse(payload))

    with pytest.raises(ValueError, match="exceeds"):
        download_arxiv_pdf("2301.12345", tmp_path, max_bytes=1024 * 1024)

    # Partial file must be cleaned up on failure.
    assert not any(tmp_path.iterdir())


def test_download_rejects_non_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(arxiv_client, "urlopen", lambda *a, **k: _FakeResponse(b"<html>not a pdf</html>"))

    with pytest.raises(ValueError, match="not a valid PDF"):
        download_arxiv_pdf("2301.12345", tmp_path)
    assert not any(tmp_path.iterdir())


def test_download_writes_valid_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    payload = b"%PDF-1.7\n%fake body"
    monkeypatch.setattr(arxiv_client, "urlopen", lambda *a, **k: _FakeResponse(payload))

    path = download_arxiv_pdf("2301.12345", tmp_path)
    assert path.exists()
    assert path.read_bytes() == payload


def test_parse_valid_xml() -> None:
    xml = f'<feed xmlns="{_ATOM}"><entry><title>Hello</title></entry></feed>'.encode()
    assert _parse_arxiv_xml(xml, "2301.12345")["title"] == "Hello"


def test_parse_rejects_entity_bomb() -> None:
    bomb = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>'
        b"<feed>&lol2;</feed>"
    )
    # defusedxml refuses the entity expansion; we degrade to empty metadata
    # rather than crashing the import request.
    assert _parse_arxiv_xml(bomb, "x") == {}
