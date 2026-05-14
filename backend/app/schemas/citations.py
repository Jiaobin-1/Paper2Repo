from __future__ import annotations

from pydantic import BaseModel


class CitationInfo(BaseModel):
    index: int
    authors: str
    title: str
    venue: str = ""
    year: str = ""
    doi: str = ""
    raw_text: str
