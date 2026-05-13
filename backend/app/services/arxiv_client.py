from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.request import urlopen

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
        root = ET.fromstring(xml_data)
    except ET.ParseError:
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


def download_arxiv_pdf(arxiv_id: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_id = arxiv_id.replace("/", "_")
    dest_path = dest_dir / f"arxiv_{safe_id}.pdf"

    url = f"{_ARXIV_PDF}/{arxiv_id}.pdf"
    try:
        with urlopen(url, timeout=60) as resp:
            dest_path.write_bytes(resp.read())
    except Exception:
        logger.warning("Failed to download arXiv PDF for %s", arxiv_id, exc_info=True)
        raise

    return dest_path


def get_arxiv_versions(arxiv_id: str) -> list[dict[str, str]]:
    base_id = re.sub(r"v\d+$", "", arxiv_id)
    metadata = fetch_arxiv_metadata(base_id)
    if metadata and metadata.get("versions"):
        return metadata["versions"]
    return [{"version": "v1", "date": ""}]
