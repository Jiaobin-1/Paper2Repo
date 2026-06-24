from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import urlencode
from urllib.request import urlopen

from defusedxml.ElementTree import fromstring as safe_xml_fromstring

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_NEW_ARXIV_ID = r"\d{4}\.\d{4,5}(?:v\d+)?"
_LEGACY_ARXIV_ID = r"[A-Za-z][A-Za-z0-9.-]*/\d{7}(?:v\d+)?"
_ARXIV_ID_PATTERN = re.compile(rf"^(?:{_NEW_ARXIV_ID}|{_LEGACY_ARXIV_ID})$", re.IGNORECASE)
_ARXIV_PREFIX_PATTERN = re.compile(r"^arXiv[:\s]+", re.IGNORECASE)
_ARXIV_URL_PATTERN = re.compile(
    rf"^(?:https?://)?(?:www\.)?arxiv\.org/(?:abs|pdf)/(?P<id>{_NEW_ARXIV_ID}|{_LEGACY_ARXIV_ID})"
    r"(?:\.pdf)?/?(?:[?#].*)?$",
    re.IGNORECASE,
)

_ARXIV_API = "https://export.arxiv.org/api/query"
_ARXIV_PDF = "https://arxiv.org/pdf"
_METADATA_MAX_BYTES = 2 * 1024 * 1024
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024
_PDF_SIGNATURE = b"%PDF-"


def extract_arxiv_id(text: str) -> str | None:
    candidate = normalize_arxiv_id(text)
    if candidate:
        return candidate
    for token in text.split():
        candidate = normalize_arxiv_id(token.strip("()[]{}<>,.;"))
        if candidate:
            return candidate
    return None


def normalize_arxiv_id(raw: str) -> str:
    candidate = raw.strip()
    url_match = _ARXIV_URL_PATTERN.fullmatch(candidate)
    candidate = url_match.group("id") if url_match else _ARXIV_PREFIX_PATTERN.sub("", candidate).strip()
    return candidate if _ARXIV_ID_PATTERN.fullmatch(candidate) else ""


def fetch_arxiv_metadata(arxiv_id: str) -> dict[str, Any]:
    normalized_id = normalize_arxiv_id(arxiv_id)
    if not normalized_id:
        return {}
    url = f"{_ARXIV_API}?{urlencode({'id_list': normalized_id})}"
    try:
        with urlopen(url, timeout=15) as response:
            xml_data = _read_limited(response, _METADATA_MAX_BYTES)
    except Exception:
        logger.warning("Failed to fetch arXiv metadata for %s", normalized_id, exc_info=True)
        return {}

    return _parse_arxiv_xml(xml_data, normalized_id)


def _parse_arxiv_xml(xml_data: bytes, arxiv_id: str) -> dict[str, Any]:
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    try:
        root = safe_xml_fromstring(xml_data)
    except Exception:
        return {}

    entry = root.find("atom:entry", ns)
    if entry is None:
        return {}

    title_el = entry.find("atom:title", ns)
    title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""

    summary_el = entry.find("atom:summary", ns)
    abstract = summary_el.text.strip().replace("\n", " ") if summary_el is not None and summary_el.text else ""

    authors = []
    for author_el in entry.findall("atom:author", ns):
        name_el = author_el.find("atom:name", ns)
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    published_el = entry.find("atom:published", ns)
    published = published_el.text.strip() if published_el is not None and published_el.text else ""

    versions = []
    for link_el in entry.findall("atom:link", ns):
        title_attr = link_el.get("title", "")
        if re.fullmatch(r"v\d+", title_attr):
            versions.append({"version": title_attr, "date": link_el.get("updated", published)})

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "published": published,
        "versions": versions,
    }


def download_arxiv_pdf(arxiv_id: str, dest_dir: Path, *, max_bytes: int | None = None) -> Path:
    normalized_id = normalize_arxiv_id(arxiv_id)
    if not normalized_id:
        raise ValueError("Invalid arXiv ID.")

    limit = max(1, max_bytes or get_settings().upload_max_bytes)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_id = normalized_id.replace("/", "_")
    dest_path = dest_dir / f"arxiv_{safe_id}_{uuid.uuid4().hex[:12]}.pdf"
    partial_path = dest_path.with_suffix(".pdf.part")
    url = f"{_ARXIV_PDF}/{normalized_id}.pdf"

    try:
        with urlopen(url, timeout=60) as response, partial_path.open("wb") as output:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > limit:
                raise ValueError(f"arXiv PDF exceeds the configured {limit // (1024 * 1024)} MB limit.")
            _copy_limited(response, output, limit)
        with partial_path.open("rb") as saved_file:
            if saved_file.read(len(_PDF_SIGNATURE)) != _PDF_SIGNATURE:
                raise ValueError("arXiv returned content that is not a PDF.")
        partial_path.replace(dest_path)
    except Exception:
        partial_path.unlink(missing_ok=True)
        logger.warning("Failed to download arXiv PDF for %s", normalized_id, exc_info=True)
        raise

    return dest_path


def get_arxiv_versions(arxiv_id: str) -> list[dict[str, str]]:
    normalized_id = normalize_arxiv_id(arxiv_id)
    if not normalized_id:
        return []
    base_id = re.sub(r"v\d+$", "", normalized_id)
    metadata = fetch_arxiv_metadata(base_id)
    if metadata and metadata.get("versions"):
        return metadata["versions"]
    return [{"version": "v1", "date": ""}]


def _read_limited(response: BinaryIO, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(_DOWNLOAD_CHUNK_SIZE, max_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError("Remote response exceeded the configured size limit.")
        chunks.append(chunk)
    return b"".join(chunks)


def _copy_limited(response: BinaryIO, output: BinaryIO, max_bytes: int) -> None:
    total = 0
    while True:
        chunk = response.read(_DOWNLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ValueError(f"arXiv PDF exceeds the configured {max_bytes // (1024 * 1024)} MB limit.")
        output.write(chunk)
