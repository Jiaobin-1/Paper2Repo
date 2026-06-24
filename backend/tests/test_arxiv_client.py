from __future__ import annotations

import io

import pytest

from app.services import arxiv_client


class FakeResponse(io.BytesIO):
    def __init__(self, content: bytes, headers: dict[str, str] | None = None):
        super().__init__(content)
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2401.12345", "2401.12345"),
        ("arXiv:2401.12345v2", "2401.12345v2"),
        ("https://arxiv.org/pdf/2401.12345.pdf", "2401.12345"),
        ("hep-th/9901001v2", "hep-th/9901001v2"),
        ("../../etc/passwd", ""),
        ("2401.12345/../../x", ""),
    ],
)
def test_normalize_arxiv_id_is_strict(raw, expected):
    assert arxiv_client.normalize_arxiv_id(raw) == expected


def test_download_arxiv_pdf_streams_and_validates_signature(tmp_path, monkeypatch):
    content = b"%PDF-1.4\nbody\n%%EOF"
    monkeypatch.setattr(
        arxiv_client,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(content, {"Content-Length": str(len(content))}),
    )

    path = arxiv_client.download_arxiv_pdf("2401.12345", tmp_path, max_bytes=1024)

    assert path.read_bytes() == content
    assert path.name.startswith("arxiv_2401.12345_")


def test_download_arxiv_pdf_removes_partial_file_when_limit_exceeded(tmp_path, monkeypatch):
    monkeypatch.setattr(
        arxiv_client,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(b"%PDF-" + b"x" * 32),
    )

    with pytest.raises(ValueError, match="exceeds the configured"):
        arxiv_client.download_arxiv_pdf("2401.12345", tmp_path, max_bytes=8)

    assert list(tmp_path.iterdir()) == []


def test_parse_arxiv_xml_rejects_entity_expansion():
    hostile = b"""<!DOCTYPE feed [<!ENTITY x 'expanded'>]>
    <feed xmlns='http://www.w3.org/2005/Atom'><entry><title>&x;</title></entry></feed>"""

    assert arxiv_client._parse_arxiv_xml(hostile, "2401.12345") == {}
