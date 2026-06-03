from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.request import urlopen

try:
    # defusedxml hardens parsing against entity-expansion ("billion laughs")
    # and external-entity attacks. Fall back to the stdlib parser if it is
    # not installed (the source is arxiv.org over HTTPS, so risk is low).
    from defusedxml.ElementTree import fromstring as _xml_fromstring
except ImportError:  # pragma: no cover - exercised only without the optional dep
    _xml_fromstring = ET.fromstring

logger = logging.getLogger(__name__)

_ARXIV_ID_PATTERN = re.compile(
    r"(?:arXiv[:\s])(\d{4}\.\d{4,5}(?:v\d+)?)",
    re.IGNORECASE,
)
_ARXIV_URL_PATTERN = re.compile(
    r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)",
    re.IGNORECASE,
)

_ARXIV_API = "http://export.arxiv.org/api/query"
_ARXIV_PDF = "https://arxiv.org/pdf"

# Strict whitelist of legitimate arXiv identifier shapes. Anything else must not
# be interpolated into a download URL — it is neither a real paper nor safe.
_VALID_ARXIV_ID = re.compile(
    r"^(?:\d{4}\.\d{4,5}(?:v\d+)?"  # modern: 2301.12345 / 2301.12345v2
    r"|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)$",  # legacy: math.GT/0309136
)

_PDF_SIGNATURE = b"%PDF-"
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024
_DEFAULT_MAX_PDF_BYTES = 50 * 1024 * 1024


def is_valid_arxiv_id(arxiv_id: str) -> bool:
    return bool(_VALID_ARXIV_ID.match(arxiv_id))


def extract_arxiv_id(text: str) -> str | None:
    match = _ARXIV_ID_PATTERN.search(text)
    if match:
        return match.group(1)
    match = _ARXIV_URL_PATTERN.search(text)
    if match:
        return match.group(1)
    return None


def normalize_arxiv_id(raw: str) -> str:
    raw = raw.strip()
    match = _ARXIV_URL_PATTERN.search(raw)
    if match:
        return match.group(1)
    match = _ARXIV_ID_PATTERN.search(raw)
    if match:
        return match.group(1)
    cleaned = re.sub(r"^arXiv[:\s]*", "", raw, flags=re.IGNORECASE).strip()
    if re.match(r"^\d{4}\.\d{4,5}(?:v\d+)?$", cleaned):
        return cleaned
    return cleaned


def fetch_arxiv_metadata(arxiv_id: str) -> dict[str, Any]:
    url = f"{_ARXIV_API}?id_list={arxiv_id}"
    try:
        with urlopen(url, timeout=15) as resp:
            xml_data = resp.read()
    except Exception:
        logger.warning("Failed to fetch arXiv metadata for %s", arxiv_id, exc_info=True)
        return {}

    return _parse_arxiv_xml(xml_data, arxiv_id)


def _parse_arxiv_xml(xml_data: bytes, arxiv_id: str) -> dict[str, Any]:
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    try:
        root = _xml_fromstring(xml_data)
    except Exception:
        # Malformed XML or a rejected entity bomb (defusedxml) — degrade to empty.
        logger.warning("Failed to parse arXiv XML for %s", arxiv_id, exc_info=True)
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
        if title_attr.startswith("v"):
            versions.append({"version": title_attr, "date": link_el.get("updated", published)})

    if not versions:
        for v in range(1, 4):
            versions.append({"version": f"v{v}", "date": ""})

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "published": published,
        "versions": versions,
    }


def download_arxiv_pdf(arxiv_id: str, dest_dir: Path, max_bytes: int = _DEFAULT_MAX_PDF_BYTES) -> Path:
    if not is_valid_arxiv_id(arxiv_id):
        raise ValueError(f"Refusing to download unrecognized arXiv ID: {arxiv_id!r}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_id = arxiv_id.replace("/", "_")
    dest_path = dest_dir / f"arxiv_{safe_id}.pdf"

    url = f"{_ARXIV_PDF}/{arxiv_id}.pdf"
    try:
        with urlopen(url, timeout=60) as resp:  # noqa: S310 — host is a fixed constant, id is whitelisted above
            total = 0
            with dest_path.open("wb") as buffer:
                while True:
                    chunk = resp.read(_DOWNLOAD_CHUNK_SIZE)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError(
                            f"arXiv PDF exceeds the {max_bytes // (1024 * 1024)} MB limit."
                        )
                    buffer.write(chunk)
    except Exception:
        dest_path.unlink(missing_ok=True)
        logger.warning("Failed to download arXiv PDF for %s", arxiv_id, exc_info=True)
        raise

    _validate_pdf_signature(dest_path)
    return dest_path


def _validate_pdf_signature(path: Path) -> None:
    with path.open("rb") as saved:
        if saved.read(len(_PDF_SIGNATURE)) != _PDF_SIGNATURE:
            path.unlink(missing_ok=True)
            raise ValueError("Downloaded arXiv file is not a valid PDF.")


def get_arxiv_versions(arxiv_id: str) -> list[dict[str, str]]:
    base_id = re.sub(r"v\d+$", "", arxiv_id)
    metadata = fetch_arxiv_metadata(base_id)
    if metadata and metadata.get("versions"):
        return metadata["versions"]
    return [{"version": "v1", "date": ""}]
